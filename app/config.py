"""Application configuration classes for StudySphere."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the repository
BASE_DIR: Path = Path(__file__).resolve().parent.parent

# Load environment variables from .env if present
load_dotenv(dotenv_path=BASE_DIR / ".env")


def get_database_uri() -> str:
    """Resolve the database URI with Supabase (PostgreSQL) support and SQLite fallback.

    Returns:
        str: Normalized database connection string.
    """
    raw_uri: str | None = os.getenv("DATABASE_URL")
    if not raw_uri:
        instance_dir: Path = BASE_DIR / "instance"
        instance_dir.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{instance_dir / 'studysphere.db'}"

    # Supabase / cloud PostgreSQL connection URLs often start with postgres://
    # SQLAlchemy requires postgresql:// or postgresql+psycopg2://
    if raw_uri.startswith("postgres://"):
        return raw_uri.replace("postgres://", "postgresql+psycopg2://", 1)
    if raw_uri.startswith("postgresql://") and not raw_uri.startswith("postgresql+"):
        return raw_uri.replace("postgresql://", "postgresql+psycopg2://", 1)

    return raw_uri


class Config:
    """Base configuration class with common parameters."""

    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-fallback-secret-key-studysphere")
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_DATABASE_URI: str = get_database_uri()
    LLM_API_KEY: str | None = os.getenv("LLM_API_KEY")


class DevelopmentConfig(Config):
    """Development environment configuration."""

    DEBUG: bool = True
    TESTING: bool = False


class TestingConfig(Config):
    """Testing environment configuration."""

    DEBUG: bool = False
    TESTING: bool = True
    SQLALCHEMY_DATABASE_URI: str = (
        os.getenv("TEST_DATABASE_URL") or "sqlite:///:memory:"
    )
    WTF_CSRF_ENABLED: bool = False


class ProductionConfig(Config):
    """Production environment configuration with strict settings."""

    DEBUG: bool = False
    TESTING: bool = False


config_by_name: dict[str, type[Config]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
