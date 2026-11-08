"""Application factory module for StudySphere."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request
from flask_login import current_user, login_required
from werkzeug.exceptions import HTTPException

from app.config import (
    Config,
    config_by_name,
    get_engine_options,
    normalize_database_uri,
)
from app.extensions import db, migrate, login_manager, csrf
from app.models.attempt import Attempt
from app.models.course import Course
from app.models.topic import Topic
from app.models.upload import Upload
from app.models.user import User
from app.services.markdown_renderer import (
    calculate_reading_time,
    render_markdown,
)
import app.models  # noqa: F401 - Register models with SQLAlchemy metadata


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure a Flask application instance.

    Args:
        config_name: Environment name ('development', 'testing', 'production').
                     Defaults to FLASK_ENV or 'development'.

    Returns:
        Flask: Initialized Flask application.
    """
    app = Flask(__name__, instance_relative_config=True)

    # Resolve configuration class
    env_name = config_name or os.getenv("FLASK_ENV", "development")
    config_class: type[Config] = config_by_name.get(
        env_name, config_by_name["default"]
    )
    app.config.from_object(config_class)

    if env_name == "production":
        secret_key = os.getenv("SECRET_KEY")
        database_url = os.getenv("DATABASE_URL")
        missing_settings = [
            name
            for name, value in (
                ("SECRET_KEY", secret_key),
                ("DATABASE_URL", database_url),
            )
            if not value
        ]
        if missing_settings:
            missing = ", ".join(missing_settings)
            raise RuntimeError(
                f"Production configuration requires environment variables: {missing}."
            )
        app.config["SECRET_KEY"] = secret_key
        app.config["SQLALCHEMY_DATABASE_URI"] = normalize_database_uri(database_url)
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = get_engine_options(
            app.config["SQLALCHEMY_DATABASE_URI"]
        )

    # Normalize relative sqlite:///instance/ paths to prevent Flask-SQLAlchemy 3.x
    # from double-prepending instance_path (e.g. instance/instance/studysphere.db)
    raw_db_uri: str = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if raw_db_uri and raw_db_uri.startswith("sqlite:///instance/"):
        rel_subpath = raw_db_uri[len("sqlite:///"):]
        abs_db_file = (Path(__file__).resolve().parent.parent / rel_subpath).resolve()
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{abs_db_file.as_posix()}"

    # Ensure instance folder exists
    instance_path = Path(app.instance_path)
    instance_path.mkdir(parents=True, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Configure authentication manager
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to access this page."
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        """Load user entity by primary key for session management."""
        try:
            return db.session.get(User, int(user_id))
        except (ValueError, TypeError):
            return None

    # Register custom template filters
    from app.services.label_service import get_label_guidance, get_label_badge_class

    app.jinja_env.filters["render_markdown"] = render_markdown
    app.jinja_env.filters["reading_time"] = calculate_reading_time
    app.jinja_env.filters["calculate_reading_time"] = calculate_reading_time
    app.jinja_env.filters["label_guidance"] = get_label_guidance
    app.jinja_env.filters["label_badge_class"] = get_label_badge_class

    # Register custom CLI commands
    from app.cli import register_cli_commands

    register_cli_commands(app)

    # Register blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.topics import topics_bp
    from app.blueprints.quiz import quiz_bp
    from app.blueprints.upload import upload_bp
    from app.blueprints.dashboard import dashboard_bp
    from app.blueprints.chat import chat_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(topics_bp, url_prefix="/topics")
    app.register_blueprint(quiz_bp, url_prefix="/quiz")
    app.register_blueprint(upload_bp, url_prefix="/upload")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(chat_bp, url_prefix="/chat")

    # Core health & index probe
    @app.route("/health", methods=["GET"])
    def health_check():
        """Health check endpoint for container probes and deployment verification."""
        return jsonify({"status": "healthy", "service": "studysphere-api"}), 200

    @app.route("/", methods=["GET"])
    def index():
        """Service root welcome endpoint, serving landing page or JSON metadata."""
        best_match = request.accept_mimetypes.best_match(["text/html", "application/json"])
        if best_match == "application/json" and request.accept_mimetypes["application/json"] > request.accept_mimetypes["text/html"]:
            return jsonify(
                {
                    "message": "Welcome to StudySphere API",
                    "status": "online",
                    "docs": "/dashboard",
                }
            ), 200
        last_attempt = None
        if current_user.is_authenticated:
            last_attempt = (
                Attempt.query.filter_by(user_id=current_user.id)
                .order_by(Attempt.created_at.desc(), Attempt.id.desc())
                .first()
            )
        return render_template("home.html", last_attempt=last_attempt)

    @app.route("/home/courses", methods=["GET"])
    @login_required
    def home_courses() -> Any:
        """Return subjects for one semester for the authenticated homepage."""
        semester = request.args.get("semester", type=int)
        if semester is None or not 1 <= semester <= 8:
            return jsonify(error="Choose a semester from 1 to 8."), 400
        courses = (
            Course.query.filter_by(semester=semester)
            .order_by(Course.code)
            .all()
        )
        return jsonify(
            courses=[
                {"id": course.id, "code": course.code, "name": course.title}
                for course in courses
            ]
        )

    @app.route("/home/topics", methods=["GET"])
    @login_required
    def home_topics() -> Any:
        """Return topics belonging only to the selected curriculum subject."""
        course_id = request.args.get("course_id", type=int)
        if course_id is None:
            return jsonify(error="Choose a subject."), 400
        course = db.session.get(Course, course_id)
        if course is None:
            return jsonify(error="Subject not found."), 404
        topics = Topic.query.filter_by(course_id=course.id).order_by(Topic.name).all()
        return jsonify(
            topics=[{"id": topic.id, "name": topic.name} for topic in topics]
        )

    @app.route("/home/uploads", methods=["GET"])
    @login_required
    def home_uploads() -> Any:
        """Return only the current student's uploaded study materials."""
        uploads = (
            Upload.query.filter_by(user_id=current_user.id)
            .order_by(Upload.created_at.desc(), Upload.id.desc())
            .all()
        )
        return jsonify(
            uploads=[
                {"id": upload.id, "title": upload.title} for upload in uploads
            ]
        )

    # Error handlers
    @app.errorhandler(404)
    def handle_not_found(error):
        """Render friendly 404 error page for missing routes or resources."""
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    @app.errorhandler(Exception)
    def handle_internal_server_error(error):
        """Handle 500 internal server errors, rollback database session, and log server-side."""
        if isinstance(error, HTTPException) and error.code != 500:
            return error
        app.logger.error("Internal Server Error caught by handler: %s", error, exc_info=True)
        try:
            db.session.rollback()
        except Exception as rollback_err:
            app.logger.warning("Database session rollback failed during 500 error handling: %s", rollback_err)
        return render_template("errors/500.html"), 500

    return app
