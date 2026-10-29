"""Application factory module for StudySphere."""

import os
from pathlib import Path
from flask import Flask, jsonify
from app.config import config_by_name, Config
from app.extensions import db, migrate
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

    # Ensure instance folder exists
    instance_path = Path(app.instance_path)
    instance_path.mkdir(parents=True, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

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
        """Service root welcome endpoint."""
        return jsonify(
            {
                "message": "Welcome to StudySphere API",
                "status": "online",
                "docs": "/dashboard",
            }
        ), 200

    return app
