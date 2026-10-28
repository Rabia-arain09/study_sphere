"""Topics blueprint for curriculum browsing (semester -> subject -> topic) and prerequisites."""

from flask import Blueprint

topics_bp: Blueprint = Blueprint("topics", __name__)
