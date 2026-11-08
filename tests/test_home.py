"""Tests for authenticated homepage learning context and chat."""

from __future__ import annotations
import json
from unittest.mock import MagicMock
from flask import Flask
from flask.testing import FlaskClient
import pytest
from app.extensions import db
from app.models.attempt import Attempt
from app.models.course import Course
from app.models.topic import Topic
from app.models.upload import Upload
from app.models.user import User


def _create_course_topic(
    *,
    code: str,
    title: str,
    semester: int,
    topic_name: str,
    content: str,
) -> tuple[Course, Topic]:
    """Create one curriculum subject and its grounded note for homepage tests."""
    course = Course(
        code=code,
        title=title,
        semester=semester,
        domain="Computer Science",
        credit_hours=3,
        contact_hours="3-0-3",
    )
    db.session.add(course)
    db.session.flush()
    topic = Topic(
        course_id=course.id,
        semester=semester,
        subject=title,
        name=topic_name,
        difficulty=1,
        content=content,
    )
    db.session.add(topic)
    db.session.flush()
    return course, topic


def _create_upload(user_id: int, title: str, text: str) -> Upload:
    """Create one saved upload without invoking the content-generation pipeline."""
    upload = Upload(
        user_id=user_id,
        source_type="text",
        title=title,
        content_hash=(str(user_id) + title).encode().hex().ljust(64, "0")[:64],
        extracted_text=text,
        summary=[],
        simple_explanation="",
        key_terms=[],
        questions=[],
    )
    db.session.add(upload)
    db.session.flush()
    return upload


def test_home_page_html_unauthenticated(client: FlaskClient) -> None:
    """Show a short visitor introduction with login and registration actions."""
    response = client.get("/", headers={"Accept": "text/html"})
    assert response.status_code == 200
    assert b"Learn with clarity. Grow with confidence." in response.data
    assert b"Sign Up" in response.data
    assert b"Login" in response.data
    assert b"Follow your curriculum" in response.data


def test_home_page_html_authenticated(auth_client: FlaskClient) -> None:
    """Show the linked learning selectors, chat, and student shortcuts."""
    response = auth_client.get("/", headers={"Accept": "text/html"})
    assert response.status_code == 200
    assert b'data-home-greeting' in response.data
    assert b'data-first-name="Test"' in response.data
    assert b"Your focused study space" not in response.data
    assert b"What do you want to learn today?" in response.data
    assert b"Other answers are marked 'Not in your note'." in response.data
    assert b'data-home-semester' in response.data
    assert b'data-home-subject' in response.data
    assert b'data-home-topic' in response.data
    assert b'data-home-conversations' in response.data
    assert b'data-home-chat-search' in response.data
    assert b'data-home-new-chat' in response.data
    assert b'data-home-sidebar-toggle' in response.data
    assert b'data-home-sidebar-collapse' in response.data
    assert b"studysphere.sidebarCollapsed" in response.data
    assert b'aria-controls="home-chat-sidebar"' in response.data
    assert b"<svg" in response.data
    assert b"No chats yet. Pick a topic and ask a question." in response.data
    assert b"My uploaded material" in response.data
    assert b"Choose a topic or your uploaded material above" in response.data
    assert b"Dashboard" in response.data
    assert b"History" in response.data


def test_home_greeting_escapes_the_users_first_name(
    app: Flask,
    client: FlaskClient,
    test_user: User,
) -> None:
    """Escape user-controlled first-name text in the authenticated greeting."""
    with app.app_context():
        user = db.session.get(User, test_user.id)
        assert user is not None
        user.name = "<Rabia>"
        db.session.commit()

    login_response = client.post(
        "/auth/login",
        data={"email": "student@example.com", "password": "SecurePassword123"},
        follow_redirects=True,
    )
    assert login_response.status_code == 200
    response = client.get("/")

    assert response.status_code == 200
    assert b'data-first-name="&lt;Rabia&gt;"' in response.data
    assert b'data-first-name="<Rabia>"' not in response.data
    assert b"<Rabia>" not in response.data


def test_home_page_shows_continue_topic_for_latest_attempt(
    auth_client: FlaskClient,
    test_user: User,
    app: Flask,
) -> None:
    """Link students to the topic associated with their latest quiz attempt."""
    with app.app_context():
        _, topic = _create_course_topic(
            code="HOME101",
            title="Homepage Learning",
            semester=5,
            topic_name="Last topic",
            content="A small test note.",
        )
        db.session.add(
            Attempt(
                user_id=test_user.id,
                topic_id=topic.id,
                score=1,
                total_questions=1,
                wrong_count=0,
                attempt_number=1,
            )
        )
        db.session.commit()
        topic_id = topic.id

    response = auth_client.get("/")
    assert response.status_code == 200
    assert b"Continue where you left off" in response.data
    assert f"/topics/{topic_id}".encode() in response.data
    assert b"Last topic" in response.data


def test_home_dropdown_endpoints_filter_subjects_and_topics(
    auth_client: FlaskClient,
    app: Flask,
) -> None:
    """Return only the selected semester's subjects and selected subject's topics."""
    with app.app_context():
        course, topic = _create_course_topic(
            code="HOME201",
            title="Semester Five Subject",
            semester=5,
            topic_name="Selected subject topic",
            content="Subject-specific note.",
        )
        _create_course_topic(
            code="HOME202",
            title="Semester Four Subject",
            semester=4,
            topic_name="Other semester topic",
            content="Another note.",
        )
        course_id = course.id
        topic_id = topic.id
        db.session.commit()

    courses_response = auth_client.get("/home/courses?semester=5")
    assert courses_response.status_code == 200
    assert courses_response.json == {
        "courses": [
            {"id": course_id, "code": "HOME201", "name": "Semester Five Subject"}
        ]
    }

    topics_response = auth_client.get(f"/home/topics?course_id={course_id}")
    assert topics_response.status_code == 200
    assert topics_response.json == {
        "topics": [{"id": topic_id, "name": "Selected subject topic"}]
    }

    assert auth_client.get("/home/courses?semester=9").status_code == 400
    assert auth_client.get("/home/topics?course_id=999999").status_code == 404


def test_home_uploads_lists_only_current_users_material(
    auth_client: FlaskClient,
    test_user: User,
    app: Flask,
) -> None:
    """Never include another student's uploaded materials in the homepage selector."""
    with app.app_context():
        owner_upload = _create_upload(test_user.id, "My notes", "My source.")
        other_user = User(
            name="Other Student",
            email="other-home@example.com",
            semester=2,
        )
        other_user.set_password("SecurePassword123")
        db.session.add(other_user)
        db.session.flush()
        foreign_upload = _create_upload(other_user.id, "Private notes", "Private.")
        owner_id = owner_upload.id
        foreign_id = foreign_upload.id
        db.session.commit()

    response = auth_client.get("/home/uploads")
    assert response.status_code == 200
    assert response.json == {"uploads": [{"id": owner_id, "title": "My notes"}]}

    forbidden_history = auth_client.get(f"/chat/history?upload_id={foreign_id}")
    assert forbidden_history.status_code == 404


def test_home_chat_uses_existing_topic_and_upload_chat_history(
    auth_client: FlaskClient,
    test_user: User,
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Send homepage selections through grounded chat routes and reload saved turns."""
    with app.app_context():
        _, topic = _create_course_topic(
            code="HOME301",
            title="Chat Subject",
            semester=5,
            topic_name="Chat Topic",
            content="Topic fact.",
        )
        upload = _create_upload(test_user.id, "Chat upload", "Upload fact.")
        topic_id = topic.id
        upload_id = upload.id
        db.session.commit()

    llm = MagicMock()
    llm.generate.side_effect = [
        json.dumps(
            {
                "covered": True,
                "refused": False,
                "answer": "Topic answer.",
                "evidence": "Topic fact.",
            }
        ),
        json.dumps(
            {
                "covered": True,
                "refused": False,
                "answer": "Upload answer.",
                "evidence": "Upload fact.",
            }
        ),
    ]
    monkeypatch.setattr("app.services.chat_service.get_llm_client", lambda: llm)

    topic_response = auth_client.post(
        f"/chat/topic/{topic_id}",
        json={"question": "Tell me the topic fact."},
    )
    upload_response = auth_client.post(
        f"/chat/upload/{upload_id}",
        json={"question": "Tell me the upload fact."},
    )
    assert topic_response.status_code == 200
    assert topic_response.json == {"answer": "Topic answer."}
    assert upload_response.status_code == 200
    assert upload_response.json == {"answer": "Upload answer."}

    topic_history = auth_client.get(f"/chat/history?topic_id={topic_id}")
    upload_history = auth_client.get(f"/chat/history?upload_id={upload_id}")
    assert [message["role"] for message in topic_history.json["messages"]] == [
        "user",
        "assistant",
    ]
    assert topic_history.json["messages"][-1]["content"] == "Topic answer."
    assert upload_history.json["messages"][-1]["content"] == "Upload answer."

    topic_prompt = llm.generate.call_args_list[0].kwargs["prompt"]
    upload_prompt = llm.generate.call_args_list[1].kwargs["prompt"]
    assert "Topic fact." in topic_prompt
    assert "Upload fact." in upload_prompt
    topic_prompt_data = json.loads(
        topic_prompt.split("UNTRUSTED_DATA_JSON:\n", 1)[1]
    )
    upload_prompt_data = json.loads(
        upload_prompt.split("UNTRUSTED_DATA_JSON:\n", 1)[1]
    )
    assert topic_prompt_data["topic_title"] == "Chat Topic"
    assert topic_prompt_data["subject"] == "Chat Subject"
    assert topic_prompt_data["source_material"] == "Topic fact."
    assert upload_prompt_data["material_title"] == "Chat upload"

    topic_page = auth_client.get(f"/topics/{topic_id}")
    assert topic_page.status_code == 200
    assert f'data-send-url="/chat/topic/{topic_id}"'.encode() in topic_page.data


def test_home_dropdown_endpoints_require_login(client: FlaskClient) -> None:
    """Protect curriculum and private-upload JSON data behind authentication."""
    assert client.get("/home/courses?semester=5").status_code == 302
    assert client.get("/home/topics?course_id=1").status_code == 302
    assert client.get("/home/uploads").status_code == 302
    assert client.get("/chat/history?topic_id=1").status_code == 302


def test_home_page_json_content_negotiation(client: FlaskClient) -> None:
    """Keep the existing JSON health metadata response for explicit API requests."""
    response = client.get("/", headers={"Accept": "application/json"})
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert data["status"] == "online"
    assert data["message"] == "Welcome to StudySphere API"
