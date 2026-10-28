"""Blueprints package exporting all modular Flask blueprints."""

from app.blueprints.auth import auth_bp
from app.blueprints.topics import topics_bp
from app.blueprints.quiz import quiz_bp
from app.blueprints.upload import upload_bp
from app.blueprints.dashboard import dashboard_bp

__all__: list[str] = [
    "auth_bp",
    "topics_bp",
    "quiz_bp",
    "upload_bp",
    "dashboard_bp",
]
