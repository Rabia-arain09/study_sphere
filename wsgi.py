"""Production WSGI entry point for Gunicorn."""

from flask import Flask

from app import create_app

app: Flask = create_app("production")
