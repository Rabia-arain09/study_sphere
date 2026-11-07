"""Tests for private, source-grounded study chat."""

from __future__ import annotations
import json
import re
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from flask import Flask, g
from flask.testing import FlaskClient
from app import create_app
from app.extensions import db
from app.models.chat_message import ChatMessage
from app.models.course import Course
from app.models.topic import Topic
from app.models.upload import Upload
from app.models.user import User
from app.services.upload_service import process_text_upload


@pytest.fixture
def chat_topic(app: Flask) -> int:
    """Create a small topic note for chat route tests."""
    with app.app_context():
        course = Course(
            code="CHAT101",
            title="Study Chat Testing",
            semester=1,
            domain="Computer Science",
            credit_hours=3,
            contact_hours="3-0-3",
        )
        db.session.add(course)
        db.session.flush()
        topic = Topic(
            course_id=course.id,
            semester=1,
            subject=course.title,
            name="Photosynthesis",
            difficulty=1,
            content="Photosynthesis uses light energy to make glucose from water "
            "and carbon dioxide. Chlorophyll absorbs light.",
        )
        db.session.add(topic)
        db.session.commit()
        return topic.id


def _mock_llm(
    monkeypatch: pytest.MonkeyPatch,
    *,
    covered: bool = True,
    refused: bool = False,
    answer: str = "Chlorophyll absorbs light.",
    evidence: str = "Chlorophyll absorbs light.",
) -> MagicMock:
    """Replace the configured LLM client with a deterministic chat response."""
    client = MagicMock()
    client.generate.return_value = json.dumps(
        {
            "covered": covered,
            "refused": refused,
            "answer": answer,
            "evidence": evidence,
        }
    )
    monkeypatch.setattr(
        "app.services.chat_service.get_llm_client",
        lambda: client,
    )
    return client


def _create_upload(user_id: int) -> int:
    """Create one uploaded study material using the configured fake upload client."""
    upload, _ = process_text_upload(
        user_id,
        "Cellular respiration converts glucose into usable energy. "
        "Mitochondria are a main site of this process.",
    )
    return upload.id


def test_topic_chat_saves_history_and_renders_escaped_messages(
    app: Flask,
    auth_client: FlaskClient,
    chat_topic: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Generate a grounded topic answer, persist it, and reload escaped history."""
    llm = _mock_llm(
        monkeypatch,
        answer="The note says <script>alert(1)</script>.",
    )
    question = "What does chlorophyll absorb?"
    response = auth_client.post(
        f"/chat/topic/{chat_topic}",
        json={"question": question},
    )

    assert response.status_code == 200
    assert response.json == {"answer": "The note says <script>alert(1)</script>."}
    prompt = llm.generate.call_args.kwargs["prompt"]
    assert "Chlorophyll absorbs light." in prompt
    assert question in prompt
    prompt_data = json.loads(prompt.split("UNTRUSTED_DATA_JSON:\n", 1)[1])
    assert prompt_data["topic_title"] == "Photosynthesis"
    assert prompt_data["subject"] == "Study Chat Testing"
    assert prompt_data["source_material"] == (
        "Photosynthesis uses light energy to make glucose from water and "
        "carbon dioxide. Chlorophyll absorbs light."
    )
    assert "tolerate spelling mistakes" in prompt.casefold()
    assert "summarize" in prompt.casefold()
    assert "must never be refused" in prompt.casefold()
    assert "not in your note:" in prompt.casefold()
    assert "clearly unrelated or harmful" in prompt.casefold()
    assert "untrusted data" in prompt.casefold()

    with app.app_context():
        messages = ChatMessage.query.filter_by(topic_id=chat_topic).order_by(
            ChatMessage.id
        ).all()
        assert [(message.role, message.content) for message in messages] == [
            ("user", question),
            ("assistant", "The note says <script>alert(1)</script>."),
        ]

    page = auth_client.get(f"/topics/{chat_topic}")
    assert page.status_code == 200
    assert b"The note says &lt;script&gt;alert(1)&lt;/script&gt;." in page.data
    assert b"<script>alert(1)</script>" not in page.data
    assert b"What does chlorophyll absorb?" in page.data
    assert b"ask-ai-fab" not in page.data
    assert b'role="dialog"' in page.data
    assert page.data.count(b'data-chat-open') == 1
    assert page.data.index(b'data-chat-open') < page.data.index(
        b'class="topic-body-layout"'
    )


def test_upload_chat_uses_summary_and_text_and_reloads_history(
    app: Flask,
    auth_client: FlaskClient,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Answer from uploaded material and show the saved chat on its view page."""
    llm = _mock_llm(
        monkeypatch,
        answer="Mitochondria are a main site.",
        evidence="Mitochondria are a main site of this process.",
    )
    with app.app_context():
        upload_id = _create_upload(test_user.id)

    response = auth_client.post(
        f"/chat/upload/{upload_id}",
        json={"question": "Where does this process mainly happen?"},
    )
    assert response.status_code == 200
    assert response.json == {"answer": "Mitochondria are a main site."}
    prompt = llm.generate.call_args.kwargs["prompt"]
    assert "Summary:" in prompt
    assert "Mitochondria are a main site of this process." in prompt

    page = auth_client.get(f"/upload/{upload_id}")
    assert page.status_code == 200
    assert b"Where does this process mainly happen?" in page.data
    assert b"Mitochondria are a main site." in page.data
    assert page.data.count(b'data-chat-open') == 1
    assert b"ask-ai-fab" not in page.data
    assert b'role="dialog"' in page.data
    assert b'Take Quiz' in page.data


def test_chat_returns_general_answer_when_model_reports_no_note_support(
    auth_client: FlaskClient,
    chat_topic: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep the model's marked general answer for a real unsupported question."""
    _mock_llm(
        monkeypatch,
        covered=False,
        answer=(
            "The note does not cover this. Not in your note: Hans Lippershey "
            "is often credited with inventing the telescope."
        ),
        evidence="",
    )
    response = auth_client.post(
        f"/chat/topic/{chat_topic}",
        json={"question": "Who invented the telescope?"},
    )
    assert response.status_code == 200
    assert response.json == {
        "answer": (
            "The note does not cover this. Not in your note: Hans Lippershey "
            "is often credited with inventing the telescope."
        )
    }


@pytest.mark.parametrize(
    "question",
    ["summarize", "wat du clorofil do?"],
)
def test_chat_passes_natural_language_requests_to_model_without_refusing(
    auth_client: FlaskClient,
    chat_topic: int,
    monkeypatch: pytest.MonkeyPatch,
    question: str,
) -> None:
    """Pass short and misspelled study prompts to the model as ordinary questions."""
    llm = _mock_llm(
        monkeypatch,
        answer="Chlorophyll absorbs light.",
    )
    response = auth_client.post(
        f"/chat/topic/{chat_topic}",
        json={"question": question},
    )

    assert response.status_code == 200
    assert response.json == {"answer": "Chlorophyll absorbs light."}
    prompt = llm.generate.call_args.kwargs["prompt"]
    prompt_data = json.loads(prompt.split("UNTRUSTED_DATA_JSON:\n", 1)[1])
    assert prompt_data["question"] == question
    assert "Tolerate spelling mistakes" in prompt


def test_chat_handles_a_clearly_unrelated_request_with_a_polite_refusal(
    auth_client: FlaskClient,
    chat_topic: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return a short refusal for a request explicitly marked as refused."""
    _mock_llm(
        monkeypatch,
        covered=False,
        refused=True,
        answer="I can't help with that. Let's focus on photosynthesis instead.",
        evidence="",
    )

    response = auth_client.post(
        f"/chat/topic/{chat_topic}",
        json={"question": "Help me do something harmful."},
    )

    assert response.status_code == 200
    assert response.json == {
        "answer": "I can't help with that. Let's focus on photosynthesis instead."
    }


def test_chat_rejects_answer_without_source_evidence(
    auth_client: FlaskClient,
    chat_topic: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject model evidence that does not appear in the topic note."""
    _mock_llm(
        monkeypatch,
        answer="Unsupported claim.",
        evidence="This excerpt is not in the note.",
    )
    response = auth_client.post(
        f"/chat/topic/{chat_topic}",
        json={"question": "What is a different fact?"},
    )
    assert response.status_code == 200
    assert response.json == {"answer": "This is not covered in this note."}


def test_chat_sends_only_the_last_six_saved_messages_as_context(
    app: Flask,
    auth_client: FlaskClient,
    chat_topic: int,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Include the six newest saved turns when generating a new answer."""
    llm = _mock_llm(monkeypatch)
    with app.app_context():
        db.session.add_all(
            [
                ChatMessage(
                    user_id=test_user.id,
                    topic_id=chat_topic,
                    role="user" if index % 2 == 0 else "assistant",
                    content=f"stored-message-{index}",
                )
                for index in range(8)
            ]
        )
        db.session.commit()

    response = auth_client.post(
        f"/chat/topic/{chat_topic}",
        json={"question": "New question"},
    )
    assert response.status_code == 200
    prompt = llm.generate.call_args.kwargs["prompt"]
    prompt_data = json.loads(prompt.split("UNTRUSTED_DATA_JSON:\n", 1)[1])
    assert [message["content"] for message in prompt_data["recent_conversation"]] == [
        f"stored-message-{index}" for index in range(2, 8)
    ]


def test_chat_check_cli_runs_one_live_request_without_saving_history(
    app: Flask,
    chat_topic: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run the chat-check command with the selected topic note and print its answer."""
    llm = _mock_llm(monkeypatch, answer="Chlorophyll absorbs light.")
    runner = app.test_cli_runner()

    result = runner.invoke(
        args=["chat-check", "--topic-id", str(chat_topic), "summarize"],
    )

    assert result.exit_code == 0
    assert result.output.strip() == "Chlorophyll absorbs light."
    prompt = llm.generate.call_args.kwargs["prompt"]
    prompt_data = json.loads(prompt.split("UNTRUSTED_DATA_JSON:\n", 1)[1])
    assert prompt_data["topic_title"] == "Photosynthesis"
    assert prompt_data["source_material"].startswith("Photosynthesis uses light")
    with app.app_context():
        assert ChatMessage.query.filter_by(topic_id=chat_topic).count() == 0


def test_chat_check_reports_invalid_model_reply_without_exposing_api_key(
    app: Flask,
    chat_topic: int,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Print parse diagnostics and raw reply safely when chat-check gets bad JSON."""
    secret = "chat-check-test-secret"
    monkeypatch.setitem(app.config, "GEMINI_API_KEY", secret)
    client = MagicMock()
    client.generate.return_value = f"not JSON {secret}"
    monkeypatch.setattr(
        "app.services.chat_service.get_llm_client",
        lambda: client,
    )
    runner = app.test_cli_runner()

    with caplog.at_level("ERROR", logger="app.services.chat_service"):
        result = runner.invoke(
            args=["chat-check", "--topic-id", str(chat_topic), "summarize"],
        )

    assert result.exit_code == 1
    assert "Chat failure type: JSONDecodeError" in result.output
    assert "Raw model reply:" in result.output
    assert f"not JSON [REDACTED_API_KEY]" in result.output
    assert secret not in result.output
    assert secret not in caplog.text
    assert "Chat model reply could not be parsed (JSONDecodeError)" in caplog.text


def test_topic_page_displays_only_the_latest_fifty_chat_messages(
    app: Flask,
    auth_client: FlaskClient,
    chat_topic: int,
    test_user: User,
) -> None:
    """Limit rendered topic chat history to the newest 50 messages."""
    with app.app_context():
        db.session.add_all(
            [
                ChatMessage(
                    user_id=test_user.id,
                    topic_id=chat_topic,
                    role="user" if index % 2 == 0 else "assistant",
                    content=f"history-message-{index}",
                )
                for index in range(55)
            ]
        )
        db.session.commit()

    response = auth_client.get(f"/topics/{chat_topic}")
    assert response.status_code == 200
    assert b"<p>history-message-4</p>" not in response.data
    assert b"<p>history-message-5</p>" in response.data
    assert b"<p>history-message-54</p>" in response.data


@pytest.mark.parametrize(
    ("resource", "question", "expected_status", "expected_error"),
    [
        ("topic", "", 400, "Please enter a question."),
        ("topic", "q" * 501, 400, "500 characters or fewer"),
        ("upload", "", 400, "Please enter a question."),
        ("upload", "q" * 501, 400, "500 characters or fewer"),
    ],
)
def test_chat_rejects_empty_and_overlong_questions(
    app: Flask,
    auth_client: FlaskClient,
    test_user: User,
    chat_topic: int,
    resource: str,
    question: str,
    expected_status: int,
    expected_error: str,
) -> None:
    """Reject invalid questions consistently for both chat resource types."""
    with app.app_context():
        upload_id = _create_upload(test_user.id) if resource == "upload" else None
    target_id = chat_topic if resource == "topic" else upload_id
    response = auth_client.post(
        f"/chat/{resource}/{target_id}",
        json={"question": question},
    )
    assert response.status_code == expected_status
    assert expected_error in response.json["error"]


def test_chat_daily_limit_counts_today_user_messages(
    app: Flask,
    auth_client: FlaskClient,
    chat_topic: int,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stop generation when today's configured count of user messages is reached."""
    app.config["CHAT_DAILY_LIMIT"] = 1
    llm = _mock_llm(monkeypatch)
    with app.app_context():
        db.session.add(
            ChatMessage(
                user_id=test_user.id,
                topic_id=chat_topic,
                role="user",
                content="Earlier question",
            )
        )
        db.session.commit()

    response = auth_client.post(
        f"/chat/topic/{chat_topic}",
        json={"question": "One more question"},
    )
    assert response.status_code == 429
    assert "chat limit of 1" in response.json["error"]
    llm.generate.assert_not_called()


def test_clear_chat_removes_only_current_resource_history(
    app: Flask,
    auth_client: FlaskClient,
    test_user: User,
    chat_topic: int,
) -> None:
    """Clear the selected chat without deleting messages from another resource."""
    with app.app_context():
        upload_id = _create_upload(test_user.id)
        db.session.add_all(
            [
                ChatMessage(
                    user_id=test_user.id,
                    topic_id=chat_topic,
                    role="user",
                    content="Topic chat",
                ),
                ChatMessage(
                    user_id=test_user.id,
                    upload_id=upload_id,
                    role="user",
                    content="Upload chat",
                ),
            ]
        )
        db.session.commit()

    response = auth_client.post(f"/chat/topic/{chat_topic}/clear", json={})
    assert response.status_code == 200
    assert response.json["success"] is True
    with app.app_context():
        assert ChatMessage.query.filter_by(topic_id=chat_topic).count() == 0
        assert ChatMessage.query.filter_by(upload_id=upload_id).count() == 1

    upload_clear = auth_client.post(f"/chat/upload/{upload_id}/clear", json={})
    assert upload_clear.status_code == 200
    with app.app_context():
        assert ChatMessage.query.filter_by(upload_id=upload_id).count() == 0


def test_chat_history_and_upload_are_private_to_the_owner(
    app: Flask,
    auth_client: FlaskClient,
    test_user: User,
    chat_topic: int,
) -> None:
    """Prevent users from seeing another chat's messages or using its upload."""
    with app.app_context():
        upload_id = _create_upload(test_user.id)
        db.session.add(
            ChatMessage(
                user_id=test_user.id,
                topic_id=chat_topic,
                role="assistant",
                content="Private first-user chat marker",
            )
        )
        other_user = User(
            name="Other Student",
            email="other-chat@example.com",
            semester=1,
        )
        other_user.set_password("OtherPassword123")
        db.session.add(other_user)
        db.session.commit()
        other_user_id = other_user.id

    other_client = app.test_client()
    with other_client.session_transaction() as other_session:
        other_session["_user_id"] = str(other_user_id)
        other_session["_fresh"] = True
    g.pop("_login_user", None)
    topic_page = other_client.get(f"/topics/{chat_topic}")
    assert topic_page.status_code == 200
    assert b"Private first-user chat marker" not in topic_page.data

    assert other_client.get(f"/upload/{upload_id}").status_code == 404
    assert other_client.post(
        f"/chat/upload/{upload_id}",
        json={"question": "Can I access this?"},
    ).status_code == 404
    assert (
        other_client.post(f"/chat/upload/{upload_id}/clear", json={}).status_code
        == 404
    )

    # The original owner continues to see their own topic message.
    g.pop("_login_user", None)
    owner_page = auth_client.get(f"/topics/{chat_topic}")
    assert b"Private first-user chat marker" in owner_page.data


def test_chat_endpoints_require_login(client: FlaskClient) -> None:
    """Require authentication for chat and clear operations."""
    assert (
        client.post("/chat/topic/1", json={"question": "Question"}).status_code
        == 302
    )
    assert client.post("/chat/topic/1/clear", json={}).status_code == 302
    assert (
        client.post("/chat/upload/1", json={"question": "Question"}).status_code
        == 302
    )
    assert client.post("/chat/upload/1/clear", json={}).status_code == 302


def test_chat_endpoints_enforce_csrf(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reject chat JSON writes without CSRF while accepting the signed header token."""
    app = create_app("testing")
    app.config["WTF_CSRF_ENABLED"] = True
    with app.app_context():
        db.create_all()
        user = User(name="CSRF Chat", email="chat-csrf@example.com", semester=1)
        user.set_password("SecurePassword123")
        course = Course(
            code="CSRFCHAT",
            title="CSRF Chat Testing",
            semester=1,
            domain="Computer Science",
            credit_hours=3,
            contact_hours="3-0-3",
        )
        db.session.add_all([user, course])
        db.session.flush()
        topic = Topic(
            course_id=course.id,
            semester=1,
            subject=course.title,
            name="CSRF Topic",
            difficulty=1,
            content="A CSRF test note.",
        )
        db.session.add(topic)
        db.session.commit()
        topic_id = topic.id

    test_client = app.test_client()
    login_html = test_client.get("/auth/login").get_data(as_text=True)
    login_token_match = re.search(
        r'name="csrf_token"[^>]*value="([^"]+)"',
        login_html,
    )
    assert login_token_match is not None
    login_response = test_client.post(
        "/auth/login",
        data={
            "email": "chat-csrf@example.com",
            "password": "SecurePassword123",
            "csrf_token": login_token_match.group(1),
        },
        follow_redirects=True,
    )
    assert login_response.status_code == 200

    page = test_client.get(f"/topics/{topic_id}").get_data(as_text=True)
    token_match = re.search(r'data-csrf-token="([^"]+)"', page)
    assert token_match is not None
    rejected = test_client.post(
        f"/chat/topic/{topic_id}",
        json={"question": "What is in this note?"},
    )
    assert rejected.status_code == 400

    _mock_llm(monkeypatch, answer="A CSRF test note.")
    accepted = test_client.post(
        f"/chat/topic/{topic_id}",
        json={"question": "What is in this note?"},
        headers={"X-CSRFToken": token_match.group(1)},
    )
    assert accepted.status_code == 200
    with app.app_context():
        assert ChatMessage.query.filter_by(topic_id=topic_id).count() == 2
        db.session.remove()
        db.drop_all()


def test_chat_migration_applies_on_fresh_sqlite(tmp_path: Path) -> None:
    """Apply the full migration chain and verify the chat schema and cascade FKs."""
    from flask_migrate import upgrade
    from sqlalchemy import inspect
    from app.config import TestingConfig

    database_path = tmp_path / "fresh_chat_migration.sqlite"
    original_uri = TestingConfig.SQLALCHEMY_DATABASE_URI
    TestingConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path.as_posix()}"
    try:
        migration_app = create_app("testing")
        with migration_app.app_context():
            upgrade()
            inspector = inspect(db.engine)
            assert "chat_message" in inspector.get_table_names()
            columns = {
                column["name"]
                for column in inspector.get_columns("chat_message")
            }
            assert {
                "id",
                "user_id",
                "topic_id",
                "upload_id",
                "role",
                "content",
                "created_at",
            } <= columns
            indexes = {
                index["name"]
                for index in inspector.get_indexes("chat_message")
            }
            assert {
                "ix_chat_message_user_topic_created",
                "ix_chat_message_user_upload_created",
                "ix_chat_message_user_role_created",
            } <= indexes
            checks = {
                constraint["name"]
                for constraint in inspector.get_check_constraints("chat_message")
            }
            assert {
                "ck_chat_message_role",
                "ck_chat_message_single_context",
            } <= checks
            foreign_keys = inspector.get_foreign_keys("chat_message")
            assert len(foreign_keys) == 3
            assert all(
                key["options"].get("ondelete") == "CASCADE"
                for key in foreign_keys
            )
            db.engine.dispose()
    finally:
        TestingConfig.SQLALCHEMY_DATABASE_URI = original_uri
