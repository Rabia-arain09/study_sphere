"""Upload blueprint for handling user uploads (text, image, URL) and OCR/LLM processing."""

from flask import Blueprint

upload_bp: Blueprint = Blueprint("upload", __name__)
