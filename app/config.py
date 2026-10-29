"""Application configuration classes for StudySphere."""

import os
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from dotenv import load_dotenv

# Base directory of the repository
BASE_DIR: Path = Path(__file__).resolve().parent.parent

# Load environment variables from .env if present
load_dotenv(dotenv_path=BASE_DIR / ".env")


def mask_host(host: str | None) -> str:
    """Mask a database hostname or IP address for safe logging and diagnostics.

    Preserves top-level and platform domains while obfuscating sensitive tenant
    identifiers and internal cluster coordinates.

    Args:
        host: Raw hostname or IP string.

    Returns:
        str: Obfuscated hostname safe for terminal display and logs.
    """
    if not host:
        return "localhost"
    if host in {"localhost", "127.0.0.1", "::1"}:
        return host

    parts = host.split(".")
    if len(parts) >= 3:
        if parts[0].lower() == "db":
            # Direct Supabase host pattern: db.<project-ref>.supabase.co
            masked_sub = parts[1][:3] + "***" if len(parts[1]) > 3 else "***"
            return f"db.{masked_sub}.{'.'.join(parts[2:])}"
        # Pooler host pattern: aws-0-us-east-1.pooler.supabase.com
        masked_first = parts[0][:4] + "***" if len(parts[0]) > 4 else "***"
        return f"{masked_first}.{'.'.join(parts[1:])}"
    elif len(parts) == 2:
        return f"{parts[0][:2]}***.{parts[1]}"
    return host[:2] + "***"


def mask_database_uri(uri: str | None) -> str:
    """Mask credentials and sensitive host details in a database URI.

    Never exposes passwords, tokens, or raw tenant subdomains in logs or CLI.

    Args:
        uri: Raw or normalized database connection string.

    Returns:
        str: Masked URI string with credentials obfuscated.
    """
    if not uri:
        return "N/A"
    if uri.startswith("sqlite"):
        return uri

    split = urlsplit(uri)
    user = split.username or ""
    if "." in user:
        # Supabase pooler username format: postgres.<project_ref>
        user_parts = user.split(".", 1)
        masked_user = f"{user_parts[0]}.***"
    elif user:
        masked_user = user
    else:
        masked_user = ""

    masked_h = mask_host(split.hostname)
    port_str = f":{split.port}" if split.port else ""
    auth_str = f"{masked_user}:***@" if (masked_user or split.password) else ""
    masked_netloc = f"{auth_str}{masked_h}{port_str}"

    return urlunsplit(
        (
            split.scheme,
            masked_netloc,
            split.path,
            split.query,
            split.fragment,
        )
    )


def normalize_database_uri(raw_uri: str | None) -> str:
    """Normalize database URI for SQLAlchemy, psycopg2 driver, and SSL mode.

    Converts legacy 'postgres://' or standard 'postgresql://' prefixes to
    'postgresql+psycopg2://', ensures 'sslmode=require' is present on PostgreSQL
    connections, and falls back to local SQLite when unset.

    Args:
        raw_uri: Raw connection string from environment or configuration.

    Returns:
        str: Fully normalized database URI suitable for SQLAlchemy engine creation.
    """
    if not raw_uri or not raw_uri.strip():
        instance_dir: Path = BASE_DIR / "instance"
        instance_dir.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{instance_dir / 'studysphere.db'}"

    uri: str = raw_uri.strip()

    # Normalize protocol scheme to postgresql+psycopg2
    if uri.startswith("postgres://"):
        uri = "postgresql+psycopg2://" + uri[len("postgres://"):]
    elif uri.startswith("postgresql://") and not uri.startswith("postgresql+"):
        uri = "postgresql+psycopg2://" + uri[len("postgresql://"):]

    # For PostgreSQL connections, enforce sslmode=require
    if uri.startswith("postgresql"):
        split_result = urlsplit(uri)
        query_params = [
            (k, v)
            for k, v in parse_qsl(split_result.query, keep_blank_values=True)
            if k.lower() != "sslmode"
        ]
        query_params.append(("sslmode", "require"))
        new_query = urlencode(query_params)
        uri = urlunsplit(
            (
                split_result.scheme,
                split_result.netloc,
                split_result.path,
                new_query,
                split_result.fragment,
            )
        )

    return uri


def get_engine_options(uri: str | None) -> dict[str, Any]:
    """Generate SQLAlchemy engine options optimized for target dialect and tier.

    For PostgreSQL (Supabase free tier), configures pool pre-ping, connection
    recycling, and bounded connection pool sizes to prevent exhaustion on
    connection poolers. For SQLite, avoids invalid pool sizing arguments.

    Args:
        uri: Database connection URI.

    Returns:
        dict[str, Any]: Engine options dictionary for SQLALCHEMY_ENGINE_OPTIONS.
    """
    if uri and uri.startswith("postgresql"):
        return {
            "pool_pre_ping": True,
            "pool_recycle": 300,
            "pool_size": 5,
            "max_overflow": 2,
        }
    return {
        "pool_pre_ping": True,
    }


def get_database_uri() -> str:
    """Resolve the active database URI with Supabase PostgreSQL and SQLite fallback.

    Returns:
        str: Normalized database connection string.
    """
    return normalize_database_uri(os.getenv("DATABASE_URL"))


class Config:
    """Base configuration class with common parameters."""

    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-fallback-secret-key-studysphere")
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_DATABASE_URI: str = get_database_uri()
    SQLALCHEMY_ENGINE_OPTIONS: dict[str, Any] = get_engine_options(
        SQLALCHEMY_DATABASE_URI
    )
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
    SQLALCHEMY_ENGINE_OPTIONS: dict[str, Any] = get_engine_options(
        SQLALCHEMY_DATABASE_URI
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
