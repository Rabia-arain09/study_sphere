"""Authentication blueprint for user registration, login, and session management."""

from flask import Blueprint

auth_bp: Blueprint = Blueprint("auth", __name__)
