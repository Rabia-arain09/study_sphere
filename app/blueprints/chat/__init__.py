"""JSON endpoints for private topic and uploaded-material study chats."""

from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Any

from flask import Blueprint, abort, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import aliased

from app.extensions import db
from app.models.chat_message import ChatMessage
from app.models.topic import Topic
from app.models.upload import Upload
from app.services.chat_service import (
    ChatDailyLimitError,
    ChatGenerationError,
    ChatInputError,
    build_upload_chat_source,
    clear_chat_history,
    load_chat_history,
    send_chat_message,
)

logger = logging.getLogger(__name__)
chat_bp: Blueprint = Blueprint("chat", __name__)


def _like_pattern(value: str) -> str:
    """Escape LIKE metacharacters in a user-provided conversation search."""
    escaped = (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
    return f"%{escaped}%"


def _conversation_preview(content: str, limit: int = 80) -> str:
    """Return a message preview no longer than the requested character limit."""
    if len(content) <= limit:
        return content
    return content[: limit - 3].rstrip() + "..."


def _isoformat(value: datetime) -> str:
    """Serialize a conversation timestamp as an ISO-8601 value."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc).isoformat()
    return value.isoformat()


@chat_bp.route("/conversations", methods=["GET"])
@login_required
def chat_conversations() -> Any:
    """List the current user's topic and upload chats, newest activity first."""
    user_id = current_user.id
    ranked_messages = (
        db.session.query(
            ChatMessage.id.label("message_id"),
            ChatMessage.topic_id.label("topic_id"),
            ChatMessage.upload_id.label("upload_id"),
            func.row_number()
            .over(
                partition_by=(ChatMessage.topic_id, ChatMessage.upload_id),
                order_by=(ChatMessage.created_at.desc(), ChatMessage.id.desc()),
            )
            .label("row_number"),
        )
        .filter(ChatMessage.user_id == user_id)
        .subquery()
    )
    query = (
        db.session.query(ChatMessage, Topic, Upload)
        .join(ranked_messages, ranked_messages.c.message_id == ChatMessage.id)
        .outerjoin(Topic, ranked_messages.c.topic_id == Topic.id)
        .outerjoin(Upload, ranked_messages.c.upload_id == Upload.id)
        .filter(ranked_messages.c.row_number == 1)
        .filter(or_(Upload.id.is_(None), Upload.user_id == user_id))
    )

    search = request.args.get("q", "").strip()
    if search:
        pattern = _like_pattern(search)
        matching_message = aliased(ChatMessage)
        message_match = (
            db.session.query(matching_message.id)
            .filter(matching_message.user_id == user_id)
            .filter(matching_message.content.ilike(pattern, escape="\\"))
            .filter(
                or_(
                    and_(
                        ranked_messages.c.topic_id.is_not(None),
                        matching_message.topic_id == ranked_messages.c.topic_id,
                        matching_message.upload_id.is_(None),
                    ),
                    and_(
                        ranked_messages.c.upload_id.is_not(None),
                        matching_message.upload_id == ranked_messages.c.upload_id,
                        matching_message.topic_id.is_(None),
                    ),
                )
            )
            .exists()
        )
        query = query.filter(
            or_(
                Topic.name.ilike(pattern, escape="\\"),
                Upload.title.ilike(pattern, escape="\\"),
                message_match,
            )
        )

    query = query.order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
    conversations: list[dict[str, Any]] = []
    for message, topic, upload in query.all():
        if topic is not None:
            conversation: dict[str, Any] = {
                "type": "topic",
                "id": topic.id,
                "title": topic.name,
                "subject": topic.subject,
                "semester": topic.semester,
                "course_id": topic.course_id,
            }
        elif upload is not None and upload.user_id == user_id:
            conversation = {
                "type": "upload",
                "id": upload.id,
                "title": upload.title,
                "subject": None,
            }
        else:
            continue
        conversation.update(
            {
                "preview": _conversation_preview(message.content),
                "last_activity": _isoformat(message.created_at),
            }
        )
        conversations.append(conversation)

    return jsonify(conversations=conversations)


@chat_bp.route(
    "/conversations/<string:conversation_type>/<int:conversation_id>",
    methods=["DELETE"],
)
@login_required
def delete_conversation(conversation_type: str, conversation_id: int) -> Any:
    """Delete one current-user conversation using the shared clear-history logic."""
    if conversation_type == "topic":
        if db.session.get(Topic, conversation_id) is None:
            abort(404)
        message_query = ChatMessage.query.filter_by(
            user_id=current_user.id,
            topic_id=conversation_id,
            upload_id=None,
        )
        topic_id = conversation_id
        upload_id = None
    elif conversation_type == "upload":
        upload = db.session.get(Upload, conversation_id)
        if upload is None or upload.user_id != current_user.id:
            abort(404)
        message_query = ChatMessage.query.filter_by(
            user_id=current_user.id,
            upload_id=conversation_id,
            topic_id=None,
        )
        topic_id = None
        upload_id = conversation_id
    else:
        abort(404)

    if not message_query.first():
        abort(404)
    deleted = clear_chat_history(
        current_user.id,
        topic_id=topic_id,
        upload_id=upload_id,
    )
    return jsonify(success=True, deleted=deleted), 200


@chat_bp.route("/history", methods=["GET"])
@login_required
def chat_history() -> Any:
    """Return saved messages for a selected topic or owned upload."""
    topic_value = request.args.get("topic_id")
    upload_value = request.args.get("upload_id")
    if bool(topic_value) == bool(upload_value):
        return jsonify(error="Choose one topic or uploaded material."), 400
    try:
        topic_id = int(topic_value) if topic_value else None
        upload_id = int(upload_value) if upload_value else None
    except ValueError:
        return jsonify(error="The selected chat is invalid."), 400

    if topic_id is not None and db.session.get(Topic, topic_id) is None:
        abort(404)
    if upload_id is not None:
        upload = db.session.get(Upload, upload_id)
        if upload is None or upload.user_id != current_user.id:
            abort(404)

    messages = load_chat_history(
        current_user.id,
        topic_id=topic_id,
        upload_id=upload_id,
    )
    return jsonify(
        messages=[
            {"role": message.role, "content": message.content}
            for message in messages
        ]
    )


def _submit_chat(
    source_text: str,
    *,
    topic_id: int | None = None,
    upload_id: int | None = None,
    topic_title: str | None = None,
    subject: str | None = None,
    material_title: str | None = None,
) -> Any:
    """Validate a JSON question and return a grounded chat response."""
    payload = request.get_json(silent=True)
    question = payload.get("question") if isinstance(payload, dict) else None
    try:
        answer = send_chat_message(
            user_id=current_user.id,
            question=question,
            source_text=source_text,
            topic_id=topic_id,
            upload_id=upload_id,
            topic_title=topic_title,
            subject=subject,
            material_title=material_title,
        )
    except ChatInputError as err:
        return jsonify(error=str(err)), 400
    except ChatDailyLimitError as err:
        return jsonify(error=str(err)), 429
    except ChatGenerationError as err:
        logger.warning("Chat generation failed for user %s: %s", current_user.id, err)
        return jsonify(error=str(err)), 502
    return jsonify(answer=answer), 200


@chat_bp.route("/topic/<int:topic_id>", methods=["POST"])
@login_required
def topic_chat(topic_id: int) -> Any:
    """Answer a question using only the selected topic's note content."""
    topic = db.session.get(Topic, topic_id)
    if topic is None:
        abort(404)
    return _submit_chat(
        topic.content or "",
        topic_id=topic.id,
        topic_title=topic.name,
        subject=topic.subject,
    )


@chat_bp.route("/topic/<int:topic_id>/clear", methods=["POST"])
@login_required
def clear_topic_chat(topic_id: int) -> Any:
    """Clear only the current user's messages for the selected topic."""
    if db.session.get(Topic, topic_id) is None:
        abort(404)
    deleted = clear_chat_history(current_user.id, topic_id=topic_id)
    return jsonify(success=True, deleted=deleted), 200


@chat_bp.route("/upload/<int:upload_id>", methods=["POST"])
@login_required
def upload_chat(upload_id: int) -> Any:
    """Answer a question using only the current user's uploaded material."""
    upload = db.session.get(Upload, upload_id)
    if upload is None or upload.user_id != current_user.id:
        abort(404)
    return _submit_chat(
        build_upload_chat_source(upload),
        upload_id=upload.id,
        material_title=upload.title,
    )


@chat_bp.route("/upload/<int:upload_id>/clear", methods=["POST"])
@login_required
def clear_upload_chat(upload_id: int) -> Any:
    """Clear only the current owner's messages for an uploaded material."""
    upload = db.session.get(Upload, upload_id)
    if upload is None or upload.user_id != current_user.id:
        abort(404)
    deleted = clear_chat_history(current_user.id, upload_id=upload_id)
    return jsonify(success=True, deleted=deleted), 200
