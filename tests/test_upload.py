"""Tests for Phase 7 Upload, LLM Client, SSRF Defense, and Quiz Evaluation."""

from __future__ import annotations
import io
import json
import struct
import zlib
from unittest.mock import MagicMock, patch
import pytest
from flask import Flask
from flask.testing import FlaskClient
import requests
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
    ImageValidationError,
    LLMGenerationError,
    SSRFProtectionError,
    URLValidationError,
    UploadValidationError,
    clean_text_input,
    fetch_url_content,
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
