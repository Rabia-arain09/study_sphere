"""Application entry point for running the StudySphere Flask server."""

import os
from flask import Flask
from app import create_app

app: Flask = create_app(os.getenv("FLASK_ENV", "development"))

if __name__ == "__main__":
    port: int = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=app.config.get("DEBUG", True))
