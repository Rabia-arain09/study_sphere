"""Upload blueprint for study material submission, LLM processing, and assessment quizzes."""

from __future__ import annotations
import logging
from typing import Any
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required
from app.extensions import db
from app.models.upload import Upload, UploadSourceType
from app.services.llm_client import LLMError
from app.services.upload_service import (
    DailyLimitExceededError,
    DocumentValidationError,
    ImageValidationError,
    LLMGenerationError,
    SSRFProtectionError,
    URLValidationError,
    UploadValidationError,
    process_document_upload,
    process_image_upload,
    process_text_upload,
    process_url_upload,
    score_upload_quiz,
)
from app.services.chat_service import load_chat_history

logger = logging.getLogger(__name__)

upload_bp: Blueprint = Blueprint("upload", __name__)


@upload_bp.route("/", methods=["GET", "POST"])
@login_required
def index() -> Any:
    """Render upload form or process text, image, document, or URL material."""
    if request.method == "POST":
        source_type = (request.form.get("source_type") or "").strip().lower()
        title = (request.form.get("title") or "").strip() or None
        user_request = (request.form.get("user_request") or "").strip() or None

        try:
            if source_type == UploadSourceType.TEXT.value:
                raw_text = request.form.get("text_content") or ""
                upload, is_new = process_text_upload(
                    user_id=current_user.id,
                    raw_text=raw_text,
                    title=title,
                    user_request=user_request,
                )
            elif source_type == UploadSourceType.IMAGE.value:
                file = request.files.get("image_file")
                if not file or not file.filename:
                    raise ImageValidationError("Please select an image file to upload.")
                file_bytes = file.read()
                upload, is_new = process_image_upload(
                    user_id=current_user.id,
                    file_bytes=file_bytes,
                    filename=file.filename,
                    title=title,
                    user_request=user_request,
                )
            elif source_type == UploadSourceType.DOCUMENT.value:
                file = request.files.get("document_file")
                if not file or not file.filename:
                    raise DocumentValidationError(
                        "Please select a PDF, PPTX, or DOCX file to upload."
                    )
                max_bytes = (
                    int(current_app.config.get("UPLOAD_MAX_DOCUMENT_MB", 10))
                    * 1024
                    * 1024
                )
                file_bytes = file.read(max_bytes + 1)
                upload, is_new = process_document_upload(
                    user_id=current_user.id,
                    file_bytes=file_bytes,
                    filename=file.filename,
                    title=title,
                    user_request=user_request,
                )
            elif source_type == UploadSourceType.URL.value:
                raw_url = (request.form.get("url_content") or "").strip()
                if not raw_url:
                    raise URLValidationError("Please enter an article or note URL.")
                upload, is_new = process_url_upload(
                    user_id=current_user.id,
                    url=raw_url,
                    title=title,
                    user_request=user_request,
                )
            else:
                raise UploadValidationError(
                    "Invalid upload source type. Please select text, image, "
                    "document, or URL."
                )

            if is_new:
                flash(
                    "Your study material was summarized and a quiz was generated successfully!",
                    "success",
                )
            else:
                flash(
                    "Loaded your existing study material summary and quiz.",
                    "info",
                )
            return redirect(url_for("upload.view_upload", upload_id=upload.id))

        except (
            UploadValidationError,
            ImageValidationError,
            URLValidationError,
            SSRFProtectionError,
            DailyLimitExceededError,
            LLMGenerationError,
            LLMError,
        ) as err:
            logger.warning("Upload failed for user %s: %s", current_user.id, err)
            flash(str(err), "danger")
            return (
                render_template(
                    "upload/index.html",
                    active_tab=source_type or "text",
                    title_input=title or "",
                    user_request_input=user_request or "",
                    text_input=request.form.get("text_content", ""),
                    url_input=request.form.get("url_content", ""),
                ),
                400,
            )
        except Exception as err:
            logger.error("Unexpected error in upload processing: %s", err, exc_info=True)
            flash(
                "An unexpected error occurred while processing your material. Please try again.",
                "danger",
            )
            return (
                render_template(
                    "upload/index.html",
                    active_tab=source_type or "text",
                    title_input=title or "",
                    user_request_input=user_request or "",
                    text_input=request.form.get("text_content", ""),
                    url_input=request.form.get("url_content", ""),
                ),
                400,
            )

    return render_template("upload/index.html", active_tab="text")


@upload_bp.route("/<int:upload_id>", methods=["GET"])
@login_required
def view_upload(upload_id: int) -> Any:
    """Display generated summary, simple explanation, and key terms for an upload."""
    upload = db.session.get(Upload, upload_id)
    if not upload or upload.user_id != current_user.id:
        abort(404)

    model_name = current_app.config.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
    return render_template(
        "upload/view.html",
        upload=upload,
        model_name=model_name,
        chat_messages=load_chat_history(current_user.id, upload_id=upload.id),
        chat_send_url=url_for("chat.upload_chat", upload_id=upload.id),
        chat_clear_url=url_for("chat.clear_upload_chat", upload_id=upload.id),
    )


@upload_bp.route("/<int:upload_id>/quiz", methods=["GET"])
@login_required
def take_quiz(upload_id: int) -> Any:
    """Render quiz assessment for the uploaded study material without answer leakage."""
    upload = db.session.get(Upload, upload_id)
    if not upload or upload.user_id != current_user.id:
        abort(404)

    saved_answers = {
        int(question_id): answer
        for question_id, answer in session.pop(
            f"upload_quiz_answers_{upload.id}", {}
        ).items()
    }
    return render_template(
        "upload/quiz.html",
        upload=upload,
        saved_answers=saved_answers,
        quiz_incomplete=session.pop(f"upload_quiz_incomplete_{upload.id}", False),
    )


@upload_bp.route("/<int:upload_id>/quiz/submit", methods=["POST"])
@login_required
def submit_quiz(upload_id: int) -> Any:
    """Score uploaded study material quiz and display model answers."""
    upload = db.session.get(Upload, upload_id)
    if not upload or upload.user_id != current_user.id:
        abort(404)

    # Gather student answers
    student_answers: dict[int, str] = {}
    for q in upload.questions:
        qid = q.get("id")
        if qid is not None:
            ans = request.form.get(f"question_{qid}", "")
            student_answers[qid] = ans

    if any(
        not student_answers.get(question.get("id"), "").strip()
        for question in upload.questions
        if question.get("id") is not None
    ):
        session[f"upload_quiz_answers_{upload.id}"] = student_answers
        session[f"upload_quiz_incomplete_{upload.id}"] = True
        flash("Please answer every question before submitting.", "warning")
        return redirect(url_for("upload.take_quiz", upload_id=upload.id))

    result = score_upload_quiz(upload, student_answers)

    return render_template(
        "upload/quiz_result.html",
        upload=upload,
        result=result,
    )


@upload_bp.route("/history", methods=["GET"])
@login_required
def history() -> Any:
    """List all uploaded study materials for the current student, newest first."""
    uploads = (
        Upload.query.filter_by(user_id=current_user.id)
        .order_by(Upload.created_at.desc())
        .all()
    )
    return render_template("upload/history.html", uploads=uploads)
