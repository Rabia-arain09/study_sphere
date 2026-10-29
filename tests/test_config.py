"""Unit tests for database URI normalization, engine options, and masking utilities."""

from urllib.parse import urlsplit, parse_qs
from flask import Flask
from app.config import (
    normalize_database_uri,
    mask_host,
    mask_database_uri,
    get_engine_options,
)
from app.cli import diagnose_database_error


def test_normalize_database_uri_fallback():
    """Verify missing, empty, or whitespace URI falls back to SQLite."""
    for empty_val in (None, "", "   "):
        res = normalize_database_uri(empty_val)
        assert res.startswith("sqlite:///")
        assert "studysphere.db" in res


def test_normalize_database_uri_postgres_prefix():
    """Verify legacy postgres:// prefix converts to postgresql+psycopg2:// with sslmode=require."""
    raw = "postgres://user:secret123@aws-0-us-east-1.pooler.supabase.com:5432/postgres"
    normalized = normalize_database_uri(raw)
    assert normalized.startswith("postgresql+psycopg2://")
    assert "sslmode=require" in normalized


def test_normalize_database_uri_postgresql_prefix():
    """Verify standard postgresql:// prefix converts to postgresql+psycopg2:// with sslmode=require."""
    raw = "postgresql://user:secret123@db.projectref.supabase.co:5432/postgres"
    normalized = normalize_database_uri(raw)
    assert normalized.startswith("postgresql+psycopg2://")
    assert "sslmode=require" in normalized


def test_normalize_database_uri_sslmode_replacement():
    """Verify existing sslmode parameters are overridden to require."""
    raw = "postgresql://user:secret123@host:5432/db?sslmode=disable&application_name=study"
    normalized = normalize_database_uri(raw)
    split = urlsplit(normalized)
    query = parse_qs(split.query)
    assert query["sslmode"] == ["require"]
    assert query["application_name"] == ["study"]


def test_normalize_database_uri_sqlite_untouched():
    """Verify SQLite URIs remain unaltered and do not append PostgreSQL SSL parameters."""
    for sqlite_uri in (
        "sqlite:///:memory:",
        "sqlite:///instance/studysphere.db",
        "sqlite:///C:/path/to/test.db",
    ):
        normalized = normalize_database_uri(sqlite_uri)
        assert normalized == sqlite_uri
        assert "sslmode" not in normalized


def test_get_engine_options_postgresql():
    """Verify PostgreSQL engine options configure pool pre-ping, recycle, and bounded pool sizes."""
    uri = "postgresql+psycopg2://u:p@h:5432/db?sslmode=require"
    opts = get_engine_options(uri)
    assert opts["pool_pre_ping"] is True
    assert opts["pool_recycle"] == 300
    assert opts["pool_size"] == 5
    assert opts["max_overflow"] == 2


def test_get_engine_options_sqlite():
    """Verify SQLite engine options avoid setting pool_size which can conflict with StaticPool."""
    for uri in ("sqlite:///:memory:", "sqlite:///instance/studysphere.db", None):
        opts = get_engine_options(uri)
        assert opts["pool_pre_ping"] is True
        assert "pool_size" not in opts
        assert "max_overflow" not in opts


def test_mask_host():
    """Verify hostname masking obfuscates sensitive tenant subdomains and cluster coordinates."""
    # Local hosts
    assert mask_host(None) == "localhost"
    assert mask_host("localhost") == "localhost"
    assert mask_host("127.0.0.1") == "127.0.0.1"

    # Supabase direct host: db.<project-ref>.supabase.co
    direct_masked = mask_host("db.abcdefghijklmnop.supabase.co")
    assert "abcdefghijklmnop" not in direct_masked
    assert direct_masked == "db.abc***.supabase.co"

    # Supabase pooler host: aws-0-us-east-1.pooler.supabase.com
    pooler_masked = mask_host("aws-0-us-east-1.pooler.supabase.com")
    assert pooler_masked == "aws-***.pooler.supabase.com"

    # Arbitrary host
    two_part = mask_host("example.com")
    assert two_part == "ex***.com"


def test_mask_database_uri_postgresql():
    """Verify mask_database_uri never exposes plaintext passwords or project IDs."""
    raw = (
        "postgresql+psycopg2://postgres.myprojectref:superSecretPass123@"
        "aws-0-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require"
    )
    masked = mask_database_uri(raw)

    # Password must NEVER appear in output
    assert "superSecretPass123" not in masked
    assert ":***@" in masked

    # Tenant project reference in username must be masked
    assert "myprojectref" not in masked
    assert "postgres.***" in masked

    # Host must be masked
    assert "aws-***.pooler.supabase.com" in masked
    assert "sslmode=require" in masked


def test_mask_database_uri_sqlite():
    """Verify SQLite database URIs pass through safely."""
    sqlite_uri = "sqlite:///instance/studysphere.db"
    assert mask_database_uri(sqlite_uri) == sqlite_uri
    assert mask_database_uri(None) == "N/A"


def test_diagnose_database_error_auth_failure():
    """Verify authentication failures generate password troubleshooting advice."""
    advice = diagnose_database_error(
        Exception("password authentication failed for user 'postgres'")
    )
    assert "[AUTH FAILURE]" in advice
    assert "DATABASE_URL" in advice
    assert "Supabase Dashboard" in advice


def test_diagnose_database_error_url_encoding():
    """Verify URL-encoding failures generate percent-encoding guidance."""
    advice = diagnose_database_error(
        Exception("could not translate host name 'p@ssword:5432'")
    )
    assert "[URL-ENCODING ISSUE]" in advice
    assert "quote_plus" in advice
    assert "%40" in advice


def test_diagnose_database_error_dns_ipv6():
    """Verify DNS and connection errors generate Session Pooler guidance."""
    advice = diagnose_database_error(
        Exception("could not translate host name: Name or service not known")
    )
    assert "[DNS / IPv6 / NETWORK ERROR]" in advice
    assert "Session Pooler" in advice
    assert "5432" in advice


def test_diagnose_database_error_ssl():
    """Verify SSL failures generate SSL guidance."""
    advice = diagnose_database_error(
        Exception("SSL connection has been closed unexpectedly")
    )
    assert "[SSL / TLS ERROR]" in advice
    assert "sslmode=require" in advice


def test_diagnose_database_error_timeout():
    """Verify connection timeout generates project paused guidance."""
    advice = diagnose_database_error(
        Exception("Connection timed out waiting for server")
    )
    assert "[PROJECT PAUSED / TIMEOUT]" in advice
    assert "Restore" in advice


def test_db_check_cli_command(app: Flask):
    """Verify db-check CLI command executes successfully against testing SQLite database."""
    runner = app.test_cli_runner()
    result = runner.invoke(args=["db-check"])

    assert result.exit_code == 0
    assert "StudySphere Database Diagnostic Probe" in result.output
    assert "Engine Version:" in result.output
    assert "Testing write/read round-trip inside transactional rollback... OK" in result.output
    assert "All database checks passed successfully!" in result.output
