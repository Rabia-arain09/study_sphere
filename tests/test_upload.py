"""Tests for Phase 7 Upload, LLM Client, SSRF Defense, and Quiz Evaluation."""

from __future__ import annotations
import io
import json
from pathlib import Path
import re
import socket
import struct
import zlib
from typing import Any
from unittest.mock import MagicMock, patch
import pytest
from flask import Flask
from flask.testing import FlaskClient
import requests
from docx import Document
from pypdf import PdfWriter
from pptx import Presentation
from pptx.util import Inches
from app import create_app
from app.extensions import db
from app.models.attempt import Attempt
from app.models.upload import Upload
from app.models.user import User
from app.services.llm_client import (
    FakeLLMClient,
    GeminiClient,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    sanitize_text,
)
from app.services.upload_service import (
    DailyLimitExceededError,
    DocumentValidationError,
    ImageValidationError,
    LLMGenerationError,
    SSRFProtectionError,
    URLValidationError,
    UploadValidationError,
    clean_text_input,
    clean_user_request,
    compute_upload_content_hash,
    fetch_url_content,
    extract_document_text,
    generate_study_artifacts,
    is_ip_blocked,
    process_image_upload,
    process_text_upload,
    process_url_upload,
    resolve_and_verify_host,
    score_upload_quiz,
    validate_and_repair_llm_payload,
    validate_image_file,
)


def _make_valid_png() -> bytes:
    """Generate minimal valid PNG binary with proper IHDR and IEND chunks."""
    header = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data)
    ihdr_chunk = struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)
    raw_scanline = b"\x00\xff\x00\x00"
    compressed_idat = zlib.compress(raw_scanline)
    idat_crc = zlib.crc32(b"IDAT" + compressed_idat)
    idat_chunk = (
        struct.pack(">I", len(compressed_idat))
        + b"IDAT"
        + compressed_idat
        + struct.pack(">I", idat_crc)
    )
    iend_crc = zlib.crc32(b"IEND")
    iend_chunk = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc)
    return header + ihdr_chunk + idat_chunk + iend_chunk


def _make_valid_jpeg() -> bytes:
    """Generate minimal valid JPEG bytes."""
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"


def _make_valid_webp() -> bytes:
    """Generate minimal valid WEBP bytes."""
    return b"RIFF\x18\x00\x00\x00WEBPVP8 \x0c\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"


def _make_text_pdf(text: str) -> bytes:
    """Create a small PDF containing selectable text without external utilities."""
    content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(content)).encode("ascii")
        + b" >>\nstream\n"
        + content
        + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


def _make_encrypted_pdf() -> bytes:
    """Create an encrypted PDF to verify unsupported protection is reported."""
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.encrypt("test-password")
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


def _make_pptx() -> bytes:
    """Create a presentation with slide text and speaker notes."""
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    shape = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(8), Inches(1))
    shape.text = "This presentation explains graph algorithms and traversal."
    slide.notes_slide.notes_text_frame.text = (
        "Speaker notes explain breadth first search and queue order."
    )
    stream = io.BytesIO()
    presentation.save(stream)
    return stream.getvalue()


def _make_docx() -> bytes:
    """Create a Word document with a paragraph and table content."""
    document = Document()
    document.add_paragraph("This document explains database normalization.")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "First normal form"
    table.cell(0, 1).text = "Each field contains one value."
    stream = io.BytesIO()
    document.save(stream)
    return stream.getvalue()


# ==============================================================================
# 1. Text Upload End-to-End
# ==============================================================================


def test_text_upload_end_to_end(auth_client: FlaskClient, app: Flask) -> None:
    """Verify end-to-end text upload, summary display, and honesty banner."""
    sample_text = (
        "Operating systems coordinate hardware resources and application software. "
        "A process is a program in execution, consisting of program code, memory regions, "
        "and runtime state. Virtual memory abstracts physical RAM using page tables and TLBs."
    )
    resp = auth_client.post(
        "/upload/",
        data={
            "source_type": "text",
            "title": "Operating Systems Architecture",
            "text_content": sample_text,
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Operating Systems Architecture" in resp.data
    # Mandated AI Honesty Notice check
    assert b"AI-generated from your upload, check it against your notes" in resp.data
    assert b"Key Summary Points" in resp.data
    assert b"Explain Simply" in resp.data
    assert b"Core Glossary" in resp.data
    assert b"Take Quiz" in resp.data

    with app.app_context():
        record = Upload.query.filter_by(title="Operating Systems Architecture").first()
        assert record is not None
        assert record.source_type == "text"
        assert len(record.summary) >= 5
        assert len(record.key_terms) >= 1
        assert len(record.questions) == 6


# ==============================================================================
# 2. Image Validation & Fake Header Check
# ==============================================================================


def test_image_signature_validation() -> None:
    """Ensure real magic bytes and chunk structures are validated; reject fake PNG headers."""
    # Valid formats
    png_mime, ext = validate_image_file(_make_valid_png(), "diagram.png")
    assert png_mime == "image/png"

    jpg_mime, ext = validate_image_file(_make_valid_jpeg(), "photo.jpg")
    assert jpg_mime == "image/jpeg"

    webp_mime, ext = validate_image_file(_make_valid_webp(), "slide.webp")
    assert webp_mime == "image/webp"

    # Fake PNG header with wrong/truncated content
    fake_png_truncated = b"\x89PNG\r\n\x1a\nfakecontent"
    with pytest.raises(ImageValidationError, match="file truncated"):
        validate_image_file(fake_png_truncated, "fake.png")

    # Fake PNG header with bogus chunk
    fake_png_bogus = b"\x89PNG\r\n\x1a\n" + b"X" * 40
    with pytest.raises(ImageValidationError, match="missing IHDR header chunk"):
        validate_image_file(fake_png_bogus, "fake.png")

    # Invalid extension
    with pytest.raises(ImageValidationError, match="Unsupported file extension"):
        validate_image_file(_make_valid_png(), "malicious.exe")


def test_image_upload_route(auth_client: FlaskClient, app: Flask) -> None:
    """Test image upload through web route with valid and fake images."""
    # Valid PNG
    data = {
        "source_type": "image",
        "title": "Circuit Diagram",
        "image_file": (io.BytesIO(_make_valid_png()), "circuit.png"),
    }
    resp = auth_client.post("/upload/", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Circuit Diagram" in resp.data

    # Fake PNG
    data_fake = {
        "source_type": "image",
        "title": "Bad Image",
        "image_file": (io.BytesIO(b"\x89PNG\r\n\x1a\ncorrupt"), "bad.png"),
    }
    resp_fake = auth_client.post("/upload/", data=data_fake, content_type="multipart/form-data", follow_redirects=False)
    assert resp_fake.status_code == 400
    assert b"Corrupt or invalid PNG image" in resp_fake.data


@pytest.mark.parametrize(
    ("filename", "file_factory", "expected_text"),
    [
        (
            "lecture.pdf",
            lambda: _make_text_pdf(
                "This is readable study material about matrix algebra and vectors."
            ),
            "matrix algebra and vectors",
        ),
        (
            "slides.pptx",
            _make_pptx,
            "Speaker notes explain breadth first search and queue order.",
        ),
        (
            "notes.docx",
            _make_docx,
            "Each field contains one value.",
        ),
    ],
)
def test_document_upload_extracts_and_saves_source(
    auth_client: FlaskClient,
    app: Flask,
    filename: str,
    file_factory: Any,
    expected_text: str,
) -> None:
    """Verify PDF, PPTX, and DOCX uploads share generation and retain the filename."""
    data = {
        "source_type": "document",
        "title": f"Material from {filename}",
        "user_request": "Focus on the key definitions",
        "document_file": (io.BytesIO(file_factory()), filename),
    }
    with patch(
        "app.services.upload_service.get_llm_client",
        return_value=FakeLLMClient(),
    ):
        response = auth_client.post(
            "/upload/",
            data=data,
            content_type="multipart/form-data",
            follow_redirects=True,
        )

    assert response.status_code == 200
    assert filename.encode() in response.data
    with app.app_context():
        upload = Upload.query.filter_by(source_ref=filename).one()
        assert upload.source_type == "document"
        assert expected_text in upload.extracted_text
        assert upload.user_request == "Focus on the key definitions"
        assert len(upload.questions) == 6


def test_document_upload_rejects_wrong_extension_and_fake_file(
    auth_client: FlaskClient,
) -> None:
    """Reject unsupported names and files whose bytes do not match their extension."""
    cases = [
        (
            "notes.txt",
            _make_text_pdf("A readable PDF with enough text for a test."),
            "Unsupported document file extension",
        ),
        ("fake.pdf", b"not a PDF document", "does not match a valid PDF"),
    ]
    for filename, payload, message in cases:
        response = auth_client.post(
            "/upload/",
            data={
                "source_type": "document",
                "document_file": (io.BytesIO(payload), filename),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code == 400
        assert message.encode() in response.data


def test_document_upload_rejects_oversized_file(auth_client: FlaskClient) -> None:
    """Reject a document above the configured 10 MB limit before parsing it."""
    payload = b"%PDF-1.4\n" + b"x" * (10 * 1024 * 1024)
    response = auth_client.post(
        "/upload/",
        data={
            "source_type": "document",
            "document_file": (io.BytesIO(payload), "large.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert b"maximum allowed limit of 10 MB" in response.data


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (b"", "uploaded document is empty"),
        (
            _make_text_pdf(""),
            "This file has no readable text. "
            "Try uploading images of the pages instead.",
        ),
    ],
)
def test_pdf_without_readable_text_has_helpful_error(
    auth_client: FlaskClient,
    payload: bytes,
    message: str,
) -> None:
    """Return clear messages for empty and scanned PDFs."""
    response = auth_client.post(
        "/upload/",
        data={
            "source_type": "document",
            "document_file": (io.BytesIO(payload), "scanned.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert message.encode() in response.data


def test_document_extraction_rejects_encrypted_and_overlong_content() -> None:
    """Reject encrypted PDFs and extracted text above the shared character limit."""
    with pytest.raises(DocumentValidationError, match="Encrypted PDF files are not supported"):
        extract_document_text(_make_encrypted_pdf(), "locked.pdf")

    with pytest.raises(DocumentValidationError, match="PDF is corrupt"):
        extract_document_text(b"%PDF-corrupt", "broken.pdf")

    with pytest.raises(UploadValidationError, match="exceeds the maximum limit of 20"):
        extract_document_text(
            _make_text_pdf("A readable document with more than twenty characters."),
            "long.pdf",
            max_chars=20,
        )


def test_document_upload_obeys_daily_limit(
    app: Flask,
    auth_client: FlaskClient,
    test_user: User,
) -> None:
    """Ensure document generation is subject to the existing daily upload quota."""
    app.config["UPLOAD_DAILY_LIMIT"] = 0
    with patch(
        "app.services.upload_service.get_llm_client",
        return_value=FakeLLMClient(),
    ):
        response = auth_client.post(
            "/upload/",
            data={
                "source_type": "document",
                "document_file": (
                    io.BytesIO(_make_text_pdf("This is a readable PDF with sufficient study text.")),
                    "limited.pdf",
                ),
            },
            content_type="multipart/form-data",
        )
    assert response.status_code == 400
    assert b"reached your daily generation limit" in response.data
    with app.app_context():
        assert Upload.query.filter_by(user_id=test_user.id).count() == 0


# ==============================================================================
# 3. Size Limits
# ==============================================================================


def test_text_size_limits() -> None:
    """Ensure text exceeding max characters is rejected with friendly error."""
    with pytest.raises(UploadValidationError, match="exceeds the maximum limit"):
        clean_text_input("A" * 20001, max_chars=20000)

    with pytest.raises(UploadValidationError, match="too short"):
        clean_text_input("too short", max_chars=20000)


def test_image_size_limits() -> None:
    """Ensure images exceeding MB limit are rejected."""
    oversized_bytes = b"\x89PNG\r\n\x1a\n" + b"0" * (4 * 1024 * 1024 + 10)
    with pytest.raises(ImageValidationError, match="exceeds the maximum allowed limit of 4 MB"):
        validate_image_file(oversized_bytes, "large.png", max_mb=4)


# ==============================================================================
# 4. URL SSRF Cases (localhost, private, loopback, link-local, redirect)
# ==============================================================================


@pytest.mark.parametrize(
    "blocked_ip",
    [
        "127.0.0.1",
        "127.0.1.1",
        "::1",
        "10.0.0.1",
        "10.254.0.1",
        "192.168.1.1",
        "192.168.0.254",
        "172.16.0.1",
        "172.31.255.255",
        "169.254.169.254",  # AWS/Cloud metadata link-local
        "fe80::1",          # IPv6 link-local
        "100.64.0.1",       # Carrier-Grade NAT
        "0.0.0.0",
        "::ffff:127.0.0.1", # IPv4-mapped IPv6 loopback
        "::ffff:192.168.1.1",# IPv4-mapped IPv6 private
    ],
)
def test_is_ip_blocked(blocked_ip: str) -> None:
    """Verify all private, loopback, link-local, and reserved IP ranges are blocked."""
    assert is_ip_blocked(blocked_ip) is True


def test_public_ip_allowed() -> None:
    """Ensure standard public IPv4/IPv6 addresses are allowed."""
    assert is_ip_blocked("8.8.8.8") is False
    assert is_ip_blocked("1.1.1.1") is False
    assert is_ip_blocked("2606:4700:4700::1111") is False


def test_url_ssrf_hostname_checks() -> None:
    """Ensure localhost and non-public hostnames are blocked before network calls."""
    with pytest.raises(SSRFProtectionError, match="blocked for security"):
        resolve_and_verify_host("localhost", 80)

    with pytest.raises(SSRFProtectionError, match="blocked for security"):
        resolve_and_verify_host("app.localhost", 80)

    with pytest.raises(SSRFProtectionError, match="blocked for security"):
        resolve_and_verify_host("127.0.0.1", 80)

    with pytest.raises(SSRFProtectionError, match="blocked for security"):
        resolve_and_verify_host("10.0.0.1", 80)

    with pytest.raises(SSRFProtectionError, match="blocked for security"):
        resolve_and_verify_host("192.168.1.1", 80)

    with pytest.raises(SSRFProtectionError, match="blocked for security"):
        resolve_and_verify_host("169.254.169.254", 80)


def test_non_http_schemes_rejected() -> None:
    """Verify non-HTTP(S) schemes are blocked immediately."""
    for bad_url in [
        "ftp://example.com/notes.txt",
        "file:///etc/passwd",
        "gopher://example.com",
        "javascript:alert(1)",
    ]:
        with pytest.raises(URLValidationError, match="Unsupported URL protocol"):
            fetch_url_content(bad_url)


def test_redirect_to_private_address_blocked() -> None:
    """Verify SSRF defense inspects redirect destinations and blocks private hops."""
    mock_resp_redirect = MagicMock()
    mock_resp_redirect.status_code = 302
    mock_resp_redirect.headers = {"Location": "http://192.168.1.5/admin"}

    with patch("requests.Session.get", return_value=mock_resp_redirect):
        with patch(
            "app.services.upload_service.resolve_and_verify_host",
            side_effect=[["93.184.216.34"], SSRFProtectionError("Access blocked")],
        ):
            with pytest.raises(SSRFProtectionError, match="Access blocked"):
                fetch_url_content("http://example.com/initial")


# ==============================================================================
# 5. Non-HTML Content-Type & BeautifulSoup Extraction
# ==============================================================================


def test_non_html_content_type_rejected() -> None:
    """Verify non-HTML/plain-text responses (e.g. PDF, audio, images) are rejected."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Type": "application/pdf"}

    with patch("requests.Session.get", return_value=mock_resp):
        with patch("app.services.upload_service.resolve_and_verify_host", return_value=["93.184.216.34"]):
            with pytest.raises(URLValidationError, match="Unsupported content type"):
                fetch_url_content("http://example.com/doc.pdf")


def test_beautifulsoup_strips_scripts_and_nav() -> None:
    """Verify BeautifulSoup cleans scripts, styles, nav, and footers from HTML."""
    html_page = """
    <!DOCTYPE html>
    <html>
    <head><style>body { color: red; }</style></head>
    <body>
        <nav><a href="/">Home Menu</a></nav>
        <script>alert("malicious script");</script>
        <main>
            <h1>Computer Architecture</h1>
            <p>Pipelining is an implementation technique whereby multiple instructions are overlapped in execution.</p>
        </main>
        <footer>Copyright 2026 Educational Corp</footer>
    </body>
    </html>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Type": "text/html; charset=utf-8"}
    mock_resp.iter_content = lambda chunk_size: [html_page.encode("utf-8")]
    mock_resp.encoding = "utf-8"

    with patch("requests.Session.get", return_value=mock_resp):
        with patch("app.services.upload_service.resolve_and_verify_host", return_value=["93.184.216.34"]):
            extracted = fetch_url_content("http://example.com/pipelining")
            assert "Computer Architecture" in extracted
            assert "Pipelining is an implementation technique" in extracted
            assert "alert" not in extracted
            assert "Home Menu" not in extracted
            assert "Copyright 2026" not in extracted


# ==============================================================================
# 6. Strict JSON Schema Validation and Automatic Retry
# ==============================================================================


def test_strict_json_validation_missing_field() -> None:
    """Ensure missing required fields raise validation errors."""
    with pytest.raises(ValueError, match="'summary' must be a JSON array"):
        validate_and_repair_llm_payload({"title": "Test"})


def test_strict_json_validation_wrong_question_count() -> None:
    """Ensure non-conforming question counts (not 3 MCQ, 1 TF, 1 Short, 1 Theory) fail."""
    bad_payload = {
        "title": "Title",
        "summary": ["Bullet 1", "Bullet 2", "Bullet 3", "Bullet 4", "Bullet 5"],
        "simple_explanation": "Simple explanation.",
        "key_terms": [{"term": "T1", "meaning": "M1"}],
        "questions": [
            {"type": "mcq", "question_text": "Q1", "options": {"A": "1", "B": "2", "C": "3", "D": "4"}, "correct_answer": "A"},
            {"type": "mcq", "question_text": "Q2", "options": {"A": "1", "B": "2", "C": "3", "D": "4"}, "correct_answer": "B"},
            # Missing 3rd MCQ, TF, Short, Theory
        ],
    }
    with pytest.raises(ValueError, match="Questions validation failed"):
        validate_and_repair_llm_payload(bad_payload)


def test_llm_retry_on_invalid_initial_json() -> None:
    """Ensure an unparseable or schema-violating first attempt triggers a retry that succeeds."""
    mock_client = MagicMock()
    # 1st call returns malformed JSON; 2nd call returns valid Fake JSON
    mock_client.generate.side_effect = [
        "Not a valid JSON response",
        FakeLLMClient().generate("test"),
    ]

    result = generate_study_artifacts("Valid material text", client=mock_client)
    assert mock_client.generate.call_count == 2
    assert "summary" in result
    assert len(result["questions"]) == 6


def test_llm_retry_exhausted_raises_error() -> None:
    """Ensure failure on both attempts raises LLMGenerationError."""
    mock_client = MagicMock()
    mock_client.generate.return_value = "Broken JSON forever"

    with pytest.raises(LLMGenerationError, match="Failed to generate valid study material"):
        generate_study_artifacts("Material", client=mock_client)


# ==============================================================================
# 7. HTML in LLM Output Is Escaped / Sanitized
# ==============================================================================


def test_html_in_llm_output_is_sanitized() -> None:
    """Ensure HTML tags injected by LLM are sanitized and stripped."""
    payload = {
        "title": "Topic <script>alert(1)</script>",
        "summary": [
            "Point 1 <img src=x onerror=alert(1)>",
            "Point 2 <b>bold</b>",
            "Point 3 <iframe>evil</iframe>",
            "Point 4 normal text",
            "Point 5 normal text",
        ],
        "simple_explanation": "<script>evil()</script>Clean explanation.",
        "key_terms": [{"term": "Term <b>1</b>", "meaning": "Meaning <script>bad</script>"}],
        "questions": [
            {"type": "mcq", "question_text": "Q1 <script>", "options": {"A": "1", "B": "2", "C": "3", "D": "4"}, "correct_answer": "A"},
            {"type": "mcq", "question_text": "Q2", "options": {"A": "1", "B": "2", "C": "3", "D": "4"}, "correct_answer": "B"},
            {"type": "mcq", "question_text": "Q3", "options": {"A": "1", "B": "2", "C": "3", "D": "4"}, "correct_answer": "C"},
            {"type": "tf", "question_text": "Q4", "options": {"True": "True", "False": "False"}, "correct_answer": "True"},
            {"type": "short", "question_text": "Q5", "correct_answer": "ans"},
            {"type": "theory", "question_text": "Q6", "correct_answer": "model ans <script>"},
        ],
    }
    repaired = validate_and_repair_llm_payload(payload)
    assert "<script>" not in repaired["title"]
    assert "<script>" not in repaired["simple_explanation"]
    assert "<img" not in repaired["summary"][0]
    assert "<iframe>" not in repaired["summary"][2]


# ==============================================================================
# 8. Daily Limit Enforced
# ==============================================================================


def test_daily_limit_enforced(app: Flask, test_user: User) -> None:
    """Ensure users cannot exceed UPLOAD_DAILY_LIMIT generations per day."""
    with app.app_context():
        # Set limit to 2 for fast verification
        app.config["UPLOAD_DAILY_LIMIT"] = 2

        # 1st generation
        u1, is_new1 = process_text_upload(test_user.id, "Unique material content number 1 here.")
        assert is_new1 is True

        # 2nd generation
        u2, is_new2 = process_text_upload(test_user.id, "Unique material content number 2 here.")
        assert is_new2 is True

        # 3rd generation -> Exceeds limit
        with pytest.raises(DailyLimitExceededError, match="reached your daily generation limit"):
            process_text_upload(test_user.id, "Unique material content number 3 here.")


# ==============================================================================
# 9. Duplicate Content Reuse (sha256 of cleaned text)
# ==============================================================================


def test_duplicate_content_reuse(app: Flask, test_user: User) -> None:
    """Ensure identical text content submitted by the same user reuses existing Upload row."""
    with app.app_context():
        app.config["UPLOAD_DAILY_LIMIT"] = 2
        text = "This is a detailed study guide about relational database normalization and Boyce-Codd normal form."

        u1, is_new1 = process_text_upload(test_user.id, text, title="Database Normalization")
        assert is_new1 is True

        # Re-upload exact same text
        u2, is_new2 = process_text_upload(test_user.id, text, title="Database Normalization")
        assert is_new2 is False
        assert u1.id == u2.id
        assert Upload.query.filter_by(user_id=test_user.id).count() == 1


# ==============================================================================
# 10. Owner-Only Access (404 for other users)
# ==============================================================================


def test_owner_only_access_returns_404(client: FlaskClient, app: Flask, test_user: User) -> None:
    """Ensure students cannot view or take quizzes on other users' uploads."""
    with app.app_context():
        # Create second user
        other_user = User(name="Other Student", email="other@example.com", semester=3)
        other_user.set_password("OtherPassword123")
        db.session.add(other_user)
        db.session.commit()

        # Create upload belonging to other_user
        u, _ = process_text_upload(other_user.id, "Material belonging strictly to other student.")
        upload_id = u.id

    # Log in as test_user (student@example.com)
    client.post(
        "/auth/login",
        data={"email": "student@example.com", "password": "SecurePassword123"},
        follow_redirects=True,
    )

    # Attempt to access other user's upload -> 404
    resp_view = client.get(f"/upload/{upload_id}")
    assert resp_view.status_code == 404

    resp_quiz = client.get(f"/upload/{upload_id}/quiz")
    assert resp_quiz.status_code == 404

    resp_submit = client.post(f"/upload/{upload_id}/quiz/submit", data={})
    assert resp_submit.status_code == 404


# ==============================================================================
# 11. Login Required
# ==============================================================================


def test_login_required(client: FlaskClient) -> None:
    """Ensure unauthenticated requests are redirected to login."""
    assert client.get("/upload/").status_code == 302
    assert client.get("/upload/1").status_code == 302
    assert client.get("/upload/1/quiz").status_code == 302
    assert client.get("/upload/history").status_code == 302


# ==============================================================================
# 12. CSRF Protection
# ==============================================================================


def test_csrf_protection_on_upload() -> None:
    """Ensure POST to /upload/ without CSRF token is rejected when CSRF is enabled."""
    app_csrf = create_app("testing")
    app_csrf.config["WTF_CSRF_ENABLED"] = True

    with app_csrf.app_context():
        db.create_all()
        user = User(name="CSRF Tester", email="csrf@test.com", semester=1)
        user.set_password("Pass1234")
        db.session.add(user)
        db.session.commit()

        test_client = app_csrf.test_client()
        # Log in without CSRF (login route has CSRF too, so fetch login page to get token)
        login_page = test_client.get("/auth/login")
        # Extract CSRF token from form
        import re
        match = re.search(r'name="csrf_token"\s+value="([^"]+)"', login_page.text)
        csrf_tok = match.group(1) if match else ""

        test_client.post(
            "/auth/login",
            data={"email": "csrf@test.com", "password": "Pass1234", "csrf_token": csrf_tok},
            follow_redirects=True,
        )

        # POST to /upload/ WITHOUT csrf_token
        resp_no_csrf = test_client.post(
            "/upload/",
            data={"source_type": "text", "text_content": "Valid study text here..."},
        )
        assert resp_no_csrf.status_code == 400

        db.session.remove()
        db.drop_all()


# ==============================================================================
# 13. Quiz Scoring, History, and No Attempt Row Creation
# ==============================================================================


def test_quiz_scoring_and_stats(auth_client: FlaskClient, app: Flask, test_user: User) -> None:
    """Verify quiz scoring evaluates MCQ, TF, short tolerant matches, and leaves theory unscored."""
    with app.app_context():
        u, _ = process_text_upload(test_user.id, "Topic notes for testing quiz answers.")
        upload_id = u.id
        initial_attempts_in_db = Attempt.query.count()

    # Answers payload
    # In FakeLLMClient:
    # Q1 MCQ: correct is C
    # Q2 MCQ: correct is A
    # Q3 MCQ: correct is B
    # Q4 TF: correct is False
    # Q5 Short: correct is DNS|Domain Name System (we submit 'the dns' to test tolerant matching)
    # Q6 Theory: student explanation
    submit_payload = {
        "question_1": "C",               # Correct
        "question_2": "A",               # Correct
        "question_3": "D",               # Wrong (correct is B)
        "question_4": "False",           # Correct
        "question_5": "  the DNS  ",     # Correct (tolerant with article/spaces)
        "question_6": "TCP ensures reliable delivery; UDP is connectionless.",
    }

    resp = auth_client.post(f"/upload/{upload_id}/quiz/submit", data=submit_payload)
    assert resp.status_code == 200
    assert b"Quiz Complete!" in resp.data
    # 4 out of 5 scorable questions correct -> 80.0%
    assert b"4.0 / 5" in resp.data
    assert b"80.0%" in resp.data
    assert b"Reference Model Answer" in resp.data

    with app.app_context():
        updated_upload = db.session.get(Upload, upload_id)
        assert updated_upload.attempts_count == 1
        assert updated_upload.last_score == 4.0
        assert updated_upload.last_total == 5
        # Verify NO Attempt row was created!
        assert Attempt.query.count() == initial_attempts_in_db


def test_upload_quiz_with_missing_answer_is_rejected_and_preserved(
    auth_client: FlaskClient, app: Flask, test_user: User
) -> None:
    """Reject an incomplete upload quiz without changing stats and preserve answers."""
    with app.app_context():
        upload, _ = process_text_upload(
            test_user.id,
            "Topic notes for testing empty quiz submissions.",
        )
        upload_id = upload.id
        attempts_before = Attempt.query.count()

    response = auth_client.post(
        f"/upload/{upload_id}/quiz/submit",
        data={
            "question_1": "C",
            "question_2": "A",
            "question_3": "D",
            "question_4": "False",
            "question_5": "DNS",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Please answer every question before submitting." in response.data
    assert re.search(rb'value="C"\s+checked', response.data)
    assert b'value="False" checked' in response.data
    assert b'value="DNS"' in response.data

    with app.app_context():
        upload = db.session.get(Upload, upload_id)
        assert upload is not None
        assert upload.attempts_count == 0
        assert upload.last_score is None
        assert Attempt.query.count() == attempts_before


def test_upload_quiz_submission_with_all_answers_is_accepted(
    auth_client: FlaskClient, app: Flask, test_user: User
) -> None:
    """Accept an uploaded-material quiz when every question has an answer."""
    with app.app_context():
        upload, _ = process_text_upload(
            test_user.id,
            "Topic notes for testing partial quiz submissions.",
        )
        upload_id = upload.id

    response = auth_client.post(
        f"/upload/{upload_id}/quiz/submit",
        data={
            "question_1": "C",
            "question_2": "A",
            "question_3": "D",
            "question_4": "False",
            "question_5": "DNS",
            "question_6": "TCP is reliable and UDP is connectionless.",
        },
    )
    assert response.status_code == 200
    assert b"Please answer every question before submitting." not in response.data

    with app.app_context():
        upload = db.session.get(Upload, upload_id)
        assert upload is not None
        assert upload.attempts_count == 1


# ==============================================================================
# 14. No Answer Leakage in Quiz HTML
# ==============================================================================


def test_no_answer_leakage_in_quiz_html(auth_client: FlaskClient, app: Flask, test_user: User) -> None:
    """Ensure the GET /upload/<id>/quiz page contains NO ground truth answers or explanations."""
    with app.app_context():
        u, _ = process_text_upload(test_user.id, "Topic notes to test quiz page security.")
        upload_id = u.id

    resp = auth_client.get(f"/upload/{upload_id}/quiz")
    assert resp.status_code == 200
    body = resp.data.decode("utf-8")

    # In FakeLLMClient, Q5 ground truth is "DNS|Domain Name System" and Q6 has model answer
    assert "DNS|Domain Name System" not in body
    assert "three-way handshake and guarantees packet delivery" not in body
    assert "correct_answer" not in body


# ==============================================================================
# 15. API Key Never Appears in Logs or Errors
# ==============================================================================


def test_api_key_scrubbing() -> None:
    """Verify GeminiClient scrubs API keys completely from all error messages and strings."""
    secret = "AIzaSySecretApiKey123456789"
    client = GeminiClient(api_key=secret)

    # Text containing secret
    raw_error = f"Error connecting to https://generativelanguage.googleapis.com/v1beta/models/gemini:generateContent?key={secret}"
    cleaned = client._sanitize(raw_error)
    assert secret not in cleaned
    assert "[REDACTED_API_KEY]" in cleaned

    # Test sanitize_text standalone
    standalone_cleaned = sanitize_text(f"Query key={secret} failed", secret_key=secret)
    assert secret not in standalone_cleaned
    assert "[REDACTED_API_KEY]" in standalone_cleaned


def test_gemini_client_error_never_exposes_key() -> None:
    """Verify GeminiClient raises LLMError with scrubbed key on requests failure."""
    secret = "AIzaSySuperSecretKey999"
    client = GeminiClient(api_key=secret)

    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = f"Invalid request key={secret} provided."

    with patch("requests.post", return_value=mock_resp):
        with pytest.raises(LLMError) as exc_info:
            client.generate("Test prompt")
        err_msg = str(exc_info.value)
        assert secret not in err_msg
        assert "[REDACTED_API_KEY]" in err_msg


# ==============================================================================
# 16. URL Bug Fix and SSRF Defense Regression Tests
# ==============================================================================


def test_geeksforgeeks_dns_resolution_and_fetch() -> None:
    """Verify public domain (www.geeksforgeeks.org) with 4 Amazon IPs is allowed and fetched."""
    gfg_addrs = [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("18.64.141.118", 443)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("18.64.141.43", 443)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("18.64.141.92", 443)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("18.64.141.97", 443)),
    ]
    html_content = (
        "<html><body><main><h1>Breadth First Search (BFS)</h1>"
        "<p>Breadth First Search is a graph traversal algorithm that explores all vertices at the "
        "present depth before moving on to the vertices at the next depth level.</p></main></body></html>"
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Type": "text/html; charset=utf-8"}
    mock_resp.iter_content = lambda chunk_size: [html_content.encode("utf-8")]
    mock_resp.encoding = "utf-8"

    with patch("socket.getaddrinfo", return_value=gfg_addrs):
        with patch("requests.Session.get", return_value=mock_resp):
            extracted = fetch_url_content(
                "https://www.geeksforgeeks.org/dsa/breadth-first-search-or-bfs-for-a-graph/"
            )
            assert "Breadth First Search" in extracted
            assert "graph traversal algorithm" in extracted


def test_public_to_public_redirect_passes() -> None:
    """Verify redirect from one public host to another public host succeeds."""
    addrs_map = {
        ("host1.example.com", 80): [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))
        ],
        ("host2.example.com", 80): [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("151.101.1.69", 80))
        ],
    }

    def fake_getaddrinfo(host, port, *args, **kwargs):
        if (host, port) in addrs_map:
            return addrs_map[(host, port)]
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]

    mock_resp1 = MagicMock()
    mock_resp1.status_code = 302
    mock_resp1.headers = {"Location": "http://host2.example.com/target"}

    mock_resp2 = MagicMock()
    mock_resp2.status_code = 200
    mock_resp2.headers = {"Content-Type": "text/html; charset=utf-8"}
    mock_resp2.iter_content = lambda chunk_size: [
        b"<html><body><h1>Redirected Public Article</h1><p>Public educational material content.</p></body></html>"
    ]
    mock_resp2.encoding = "utf-8"

    with patch("socket.getaddrinfo", side_effect=fake_getaddrinfo):
        with patch("requests.Session.get", side_effect=[mock_resp1, mock_resp2]):
            content = fetch_url_content("http://host1.example.com/initial")
            assert "Redirected Public Article" in content


@pytest.mark.parametrize(
    "private_redirect_url",
    [
        "http://127.0.0.1/admin",
        "http://10.0.0.1/internal-status",
        "http://169.254.169.254/latest/meta-data/",
    ],
)
def test_redirect_to_blocked_destinations(private_redirect_url: str) -> None:
    """Verify redirects to 127.0.0.1, 10.x, or 169.254.169.254 are blocked."""
    mock_resp = MagicMock()
    mock_resp.status_code = 302
    mock_resp.headers = {"Location": private_redirect_url}

    with patch(
        "socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))],
    ):
        with patch("requests.Session.get", return_value=mock_resp):
            with pytest.raises(SSRFProtectionError, match="blocked for security reasons"):
                fetch_url_content("http://public.example.com/start")


def test_host_resolving_to_mixed_public_and_private_is_blocked() -> None:
    """Ensure host resolving to 1 public and 1 private address is completely blocked."""
    mixed_addrs = [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("18.64.141.118", 443)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.1", 443)),
    ]
    with patch("socket.getaddrinfo", return_value=mixed_addrs):
        with pytest.raises(SSRFProtectionError) as exc_info:
            resolve_and_verify_host("mixed.example.com", 443)
        assert "blocked address '192.168.1.1'" in str(exc_info.value)
        assert "private-network" in str(exc_info.value)


@pytest.mark.parametrize(
    "ipv6_blocked",
    [
        "::1",
        "::ffff:127.0.0.1",
        "::ffff:192.168.1.1",
        "::ffff:169.254.169.254",
        "::ffff:8.8.8.8",
    ],
)
def test_ipv6_loopback_and_ipv4_mapped_ipv6_blocked(ipv6_blocked: str) -> None:
    """Verify IPv6 loopback and IPv4-mapped IPv6 are blocked."""
    assert is_ip_blocked(ipv6_blocked) is True
    with pytest.raises(SSRFProtectionError, match="blocked for security reasons"):
        resolve_and_verify_host(ipv6_blocked, 80)


def test_error_message_distinguishes_host_from_ip() -> None:
    """Ensure host name is never called an IP address in error messages."""
    # 1. Hostname blocked
    with pytest.raises(SSRFProtectionError) as exc_host:
        resolve_and_verify_host("internal.localhost", 80)
    msg_host = str(exc_host.value)
    assert "Access to host 'internal.localhost'" in msg_host
    assert "Access to IP address" not in msg_host
    assert "points to a private or blocked network" in msg_host

    # 2. IP literal blocked
    with pytest.raises(SSRFProtectionError) as exc_ip:
        resolve_and_verify_host("127.0.0.1", 80)
    msg_ip = str(exc_ip.value)
    assert "Access to IP address '127.0.0.1'" in msg_ip
    assert "private or blocked network" in msg_ip


def test_friendly_error_on_http_403_and_401() -> None:
    """Ensure 403 / 401 returns friendly message suggesting pasting text directly."""
    mock_403 = MagicMock()
    mock_403.status_code = 403
    with patch(
        "socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))],
    ):
        with patch("requests.Session.get", return_value=mock_403):
            with pytest.raises(URLValidationError) as exc:
                fetch_url_content("http://protected-site.com/doc")
            err_text = str(exc.value)
            assert "refused the request (HTTP 403)" in err_text
            assert "paste the text directly" in err_text


# ==============================================================================
# 17. User Request ("What do you want to do with this material?") Tests
# ==============================================================================


def test_instruction_passed_to_both_prompts_inside_delimiters() -> None:
    """Verify user request instruction is passed to both study guide and quiz prompts inside delimiters."""
    guide_resp = json.dumps({
        "title": "Computer Networking",
        "extracted_text": "",
        "summary": ["Point 1", "Point 2", "Point 3", "Point 4", "Point 5"],
        "simple_explanation": "Simple explanation.",
        "key_terms": [{"term": "TCP", "meaning": "Transmission Control Protocol."}],
    })
    quiz_resp = json.dumps({
        "questions": [
            {"id": 1, "type": "mcq", "question_text": "Q1", "options": {"A": "1", "B": "2", "C": "3", "D": "4"}, "correct_answer": "A", "explanation": "E"},
            {"id": 2, "type": "mcq", "question_text": "Q2", "options": {"A": "1", "B": "2", "C": "3", "D": "4"}, "correct_answer": "B", "explanation": "E"},
            {"id": 3, "type": "mcq", "question_text": "Q3", "options": {"A": "1", "B": "2", "C": "3", "D": "4"}, "correct_answer": "C", "explanation": "E"},
            {"id": 4, "type": "tf", "question_text": "Q4", "options": {"True": "True", "False": "False"}, "correct_answer": "True", "explanation": "E"},
            {"id": 5, "type": "short", "question_text": "Q5", "correct_answer": "ans", "explanation": "E"},
            {"id": 6, "type": "theory", "question_text": "Q6", "correct_answer": "model answer", "explanation": "E"},
        ]
    })
    mock_client = MagicMock()
    mock_client.generate.side_effect = [guide_resp, quiz_resp]

    user_req = "Focus on definitions and key terms"
    generate_study_artifacts(
        material_text="Computer networking fundamentals notes.",
        client=mock_client,
        user_request=user_req,
    )

    assert mock_client.generate.call_count == 2
    for call in mock_client.generate.call_args_list:
        prompt_arg = call.kwargs.get("prompt") or call.args[0]
        assert "<<<USER_REQUEST_START>>>" in prompt_arg
        assert user_req in prompt_arg
        assert "<<<USER_REQUEST_END>>>" in prompt_arg
        assert "USER REQUEST RULES:" in prompt_arg
        assert "prompt-injection defense remains absolute" in prompt_arg


def test_instruction_length_limited_and_escaped_on_view(
    auth_client: FlaskClient, app: Flask, test_user: User
) -> None:
    """Ensure user request is capped at 500 chars and HTML is properly escaped on view page."""
    long_request = ("Explain simply and clearly. " * 30)[:600]
    raw_xss_request = "<script>alert('xss')</script> Focus on exam review."

    with app.app_context():
        u1, _ = process_text_upload(
            test_user.id,
            "Valid educational text content about distributed systems.",
            user_request=long_request,
        )
        assert len(u1.user_request) <= 500

        u2, _ = process_text_upload(
            test_user.id,
            "Another educational text content about algorithms.",
            user_request=raw_xss_request,
        )
        u2_id = u2.id

    resp = auth_client.get(f"/upload/{u2_id}")
    assert resp.status_code == 200
    body = resp.data.decode("utf-8")
    assert "Your request:" in body
    # Verify script tag was escaped and not rendered executable
    assert "<script>alert" not in body
    assert "Focus on exam review" in body


def test_different_instruction_creates_new_upload_and_same_reuses(
    app: Flask, test_user: User
) -> None:
    """Verify different instructions create new uploads, while identical instruction reuses existing."""
    material = "Database indexing using B-Trees and Hash indexes for fast point queries."

    with app.app_context():
        # First upload with instruction A
        u1, is_new1 = process_text_upload(
            test_user.id,
            material,
            user_request="Explain this simply",
        )
        assert is_new1 is True

        # Same text with same instruction A reuses u1
        u1_again, is_new1_again = process_text_upload(
            test_user.id,
            material,
            user_request="Explain this simply",
        )
        assert is_new1_again is False
        assert u1_again.id == u1.id

        # Same text with different instruction B creates new upload u2
        u2, is_new2 = process_text_upload(
            test_user.id,
            material,
            user_request="Prepare me for an exam",
        )
        assert is_new2 is True
        assert u2.id != u1.id


def test_existing_uploads_without_instruction_continue_to_work(
    app: Flask, test_user: User, auth_client: FlaskClient
) -> None:
    """Verify backward compatibility: uploads without instruction match legacy hashes and view safely."""
    material = "Software engineering principles including modularity, cohesion, and coupling."

    with app.app_context():
        # Legacy upload with user_request=None
        u_legacy = Upload(
            user_id=test_user.id,
            source_type="text",
            source_ref=None,
            title="Software Engineering Principles",
            content_hash=compute_upload_content_hash(clean_text_input(material)),
            user_request=None,
            extracted_text=material,
            summary=["Summary point 1", "Summary point 2", "Summary point 3", "Summary point 4", "Summary point 5"],
            simple_explanation="Modularity is like building with Lego blocks.",
            key_terms=[{"term": "Cohesion", "meaning": "How closely related elements are."}],
            questions=[],
        )
        db.session.add(u_legacy)
        db.session.commit()
        legacy_id = u_legacy.id

        # Verify that process_text_upload without user_request reuses this upload
        u_matched, is_new = process_text_upload(
            test_user.id,
            material,
            user_request=None,
        )
        assert is_new is False
        assert u_matched.id == legacy_id

    # View page renders properly without crashing when user_request is None
    resp = auth_client.get(f"/upload/{legacy_id}")
    assert resp.status_code == 200
    assert b"Software Engineering Principles" in resp.data
    assert b"Your request:" not in resp.data


def test_migration_applies_on_fresh_sqlite(tmp_path: Path) -> None:
    """Verify all migrations apply cleanly on a fresh SQLite database."""
    from app.config import TestingConfig
    fresh_db = tmp_path / "fresh_migration_test.db"
    orig_uri = TestingConfig.SQLALCHEMY_DATABASE_URI
    TestingConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{fresh_db.as_posix()}"
    try:
        test_app = create_app("testing")
        with test_app.app_context():
            from flask_migrate import upgrade
            upgrade()
            test_app.extensions["migrate"].db.engine.dispose()
    finally:
        TestingConfig.SQLALCHEMY_DATABASE_URI = orig_uri

    # Verify uploads table exists with user_request column
    import sqlite3
    con = sqlite3.connect(fresh_db.as_posix())
    cur = con.cursor()
    columns = [col[1] for col in cur.execute("PRAGMA table_info(uploads)").fetchall()]
    con.close()
    assert "user_request" in columns
    assert "content_hash" in columns
    assert "summary" in columns
