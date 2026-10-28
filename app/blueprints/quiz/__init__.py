"""Quiz blueprint for taking tests, recording attempts, and triggering ML evaluation."""

from flask import Blueprint

quiz_bp: Blueprint = Blueprint("quiz", __name__)
