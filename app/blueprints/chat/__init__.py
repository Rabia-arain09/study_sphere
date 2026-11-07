"""JSON endpoints for private topic and uploaded-material study chats."""

from __future__ import annotations
import logging
from typing import Any
from flask import Blueprint, abort, jsonify, request
from flask_login import current_user, login_required
from app.extensions import db
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
