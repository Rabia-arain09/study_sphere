"""Application factory module for StudySphere."""

from __future__ import annotations
import os
from pathlib import Path
from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException
from app.config import config_by_name, Config
from app.extensions import db, migrate, login_manager, csrf
from app.services.markdown_renderer import (
    calculate_reading_time,
    render_markdown,
)
import app.models  # noqa: F401 - Register models with SQLAlchemy metadata
from app.models.user import User


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

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(topics_bp, url_prefix="/topics")
    app.register_blueprint(quiz_bp, url_prefix="/quiz")
    app.register_blueprint(upload_bp, url_prefix="/upload")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")

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
        return render_template("home.html")

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
