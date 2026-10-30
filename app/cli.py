"""Database diagnostic and management CLI commands for StudySphere."""

import sys
from urllib.parse import urlsplit
import click
from flask import Flask, current_app
from flask.cli import with_appcontext
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from app.config import mask_database_uri, mask_host
from app.extensions import db


def diagnose_database_error(error: Exception) -> str:
    """Analyze a database connection or execution error and produce actionable troubleshooting guidance.

    Args:
        error: Caught exception during database operations.

    Returns:
        str: Human-readable diagnostic recommendations and remediation steps.
    """
    msg: str = str(error).lower()
    advice: list[str] = []

    # 1. Wrong password / authentication failure
    if any(
        k in msg
        for k in (
            "password authentication failed",
            "28p01",
            "authentication failed",
            "auth failed",
        )
    ):
        advice.append(
            "[AUTH FAILURE]: Database password was rejected by the server.\n"
            "  * Verify the password in DATABASE_URL inside your .env file.\n"
            "  * Ensure you are using the database password assigned when creating the Supabase project\n"
            "    (NOT your personal Supabase web login password).\n"
            "  * You can reset your database password in the Supabase Dashboard under\n"
            "    Project Settings > Database > Database password."
        )

    # 2. Special characters needing URL-encoding
    if any(
        k in msg
        for k in (
            "could not translate host name",
            "invalid dsn",
            "bad connection",
            "password authentication failed",
            "missing port",
            "valueerror",
        )
    ):
        advice.append(
            "[URL-ENCODING ISSUE]: Special characters in password or connection credentials.\n"
            "  * If your database password contains characters like @, :, /, ?, #, [, ], %, +, or &,\n"
            "    they MUST be percent-encoded (URL-encoded) in DATABASE_URL.\n"
            "  * In Python: urllib.parse.quote_plus('your_password')\n"
            "  * Common substitutions: '@' -> '%40', '#' -> '%23', '+' -> '%2B', '%' -> '%25'."
        )

    # 3. DNS / IPv6 error / Host unreachable
    if any(
        k in msg
        for k in (
            "could not translate host name",
            "name or service not known",
            "getaddrinfo failed",
            "network is unreachable",
            "connection refused",
            "nodename nor servname",
        )
    ):
        advice.append(
            "[DNS / IPv6 / NETWORK ERROR]: Unable to resolve or reach the database host.\n"
            "  * Supabase direct hosts (db.<project-ref>.supabase.co) resolve only to IPv6 addresses on some networks,\n"
            "    which fails on ISPs or environments without full IPv6 routing.\n"
            "  * FIX: Switch to the Supabase Session Pooler (IPv4 compatible).\n"
            "    Navigate to Supabase Dashboard > Settings > Database > Connection Pooling.\n"
            "    Select Mode: 'Session' and port 5432 (e.g., aws-0-<region>.pooler.supabase.com).\n"
            "  * Ensure active internet connectivity and that outbound port 5432 is accessible."
        )

    # 4. SSL error
    if any(k in msg for k in ("ssl", "certificate", "encryption", "sslv3")):
        advice.append(
            "[SSL / TLS ERROR]: SSL handshake or negotiation failed.\n"
            "  * Supabase requires SSL encryption on all connections.\n"
            "  * Ensure your DATABASE_URL includes '?sslmode=require'.\n"
            "  * StudySphere automatically normalizes and attaches sslmode=require to PostgreSQL URIs."
        )

    # 5. Project paused / Inactivity
    if any(
        k in msg
        for k in (
            "timeout",
            "timed out",
            "connection refused",
            "server closed the connection",
        )
    ):
        advice.append(
            "[PROJECT PAUSED / TIMEOUT]: Connection timed out or server terminated the connection.\n"
            "  * Supabase free tier projects automatically pause after 7 days of inactivity.\n"
            "  * Log in to https://supabase.com/dashboard and click 'Restore' on your project."
        )

    if not advice:
        advice.append(
            "[GENERAL DATABASE ERROR]: Review the exception details and verify that DATABASE_URL\n"
            "  adheres to: postgresql+psycopg2://<user>:<password>@<host>:5432/<dbname>?sslmode=require"
        )

    return "\n\n".join(advice)


@click.command("db-check")
@with_appcontext
def db_check_command() -> None:
    """Diagnose database connectivity, inspect metadata, and verify read/write transactions."""
    uri: str = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    masked_uri: str = mask_database_uri(uri)

    split = urlsplit(uri)
    dialect_driver = split.scheme or "unknown"
    host_raw = split.hostname or "localhost"
    masked_h = mask_host(host_raw)
    database_name = split.path.lstrip("/") or "in-memory"

    click.echo("=" * 60)
    click.echo(" StudySphere Database Diagnostic Probe")
    click.echo("=" * 60)
    click.echo(f"> Configured Driver : {dialect_driver}")
    click.echo(f"> Database Host     : {masked_h}")
    click.echo(f"> Database Name     : {database_name}")
    click.echo(f"> Masked URI        : {masked_uri}")
    click.echo("-" * 60)

    try:
        # Step 1: Establish connection
        click.echo("[1/4] Connecting to database...", nl=False)
        with db.engine.connect() as conn:
            click.echo(" OK")

            # Step 2: Query database version
            click.echo("[2/4] Querying engine version...", nl=False)
            if db.engine.dialect.name == "postgresql":
                version_info = conn.execute(text("SELECT version();")).scalar()
            else:
                version_info = conn.execute(text("SELECT sqlite_version();")).scalar()
                version_info = f"SQLite {version_info}"
            click.echo(f"\n      Engine Version: {version_info}")

            # Step 3: Inspect existing tables
            click.echo("[3/4] Inspecting existing database tables...")
            inspector = inspect(db.engine)
            tables = sorted(inspector.get_table_names())
            if tables:
                click.echo(f"      Found {len(tables)} table(s): {', '.join(tables)}")
            else:
                click.echo("      Found 0 tables (database is clean / unmigrated).")

            # Step 4: Write / Read round-trip in rolled back transaction
            click.echo(
                "[4/4] Testing write/read round-trip inside transactional rollback...",
                nl=False,
            )
            # Reset any ambient connection autobegin state before starting the explicit test transaction
            conn.rollback()
            with conn.begin() as trans:
                conn.execute(
                    text(
                        "CREATE TEMPORARY TABLE _studysphere_probe (id INT, payload VARCHAR(100))"
                    )
                )
                conn.execute(
                    text(
                        "INSERT INTO _studysphere_probe (id, payload) VALUES (:id, :val)"
                    ),
                    {"id": 1, "val": "studysphere_probe_ok"},
                )
                read_back = conn.execute(
                    text("SELECT payload FROM _studysphere_probe WHERE id = :id"),
                    {"id": 1},
                ).scalar()

                if read_back != "studysphere_probe_ok":
                    raise RuntimeError(
                        f"Round-trip mismatch: expected 'studysphere_probe_ok', got '{read_back}'"
                    )

                trans.rollback()
            click.echo(" OK (cleanly rolled back)")

        click.echo("=" * 60)
        click.echo(" All database checks passed successfully!")
        click.echo("=" * 60)

    except (SQLAlchemyError, Exception) as exc:
        click.echo(" FAILED\n")
        click.echo("!" * 60)
        click.echo(" DATABASE PROBE ENCOUNTERED AN ERROR")
        click.echo("!" * 60)
        click.echo(f"Error Type: {exc.__class__.__name__}")
        safe_msg = str(exc)
        if split.password:
            safe_msg = safe_msg.replace(split.password, "***")
        click.echo(f"Details   : {safe_msg}")
        click.echo("\n--- Recommended Troubleshooting & Human-Readable Fixes ---")
        click.echo(diagnose_database_error(exc))
        click.echo("!" * 60)
        sys.exit(1)


@click.command("load-curriculum")
@click.option(
    "--data-dir",
    default="data",
    help="Directory containing the 4 curriculum CSV files (default: data).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Validate and stage data in a rolled-back transaction without saving.",
)
@with_appcontext
def load_curriculum_command(data_dir: str, dry_run: bool) -> None:
    """Validate, parse, and idempotently ingest curriculum CSV files."""
    from app.services.curriculum_loader import (
        CurriculumLoader,
        CurriculumValidationError,
        MissingDataFileError,
    )

    try:
        loader = CurriculumLoader(data_dir=data_dir)
        summary = loader.load(dry_run=dry_run)
        click.echo(summary.format_cli_output())
    except MissingDataFileError as err:
        click.echo(f"Error: {err}", err=True)
        sys.exit(1)
    except CurriculumValidationError as err:
        click.echo(f"Error: {err}", err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(f"Curriculum ingestion failed unexpectedly: {exc}", err=True)
        sys.exit(1)


def register_cli_commands(app: Flask) -> None:
    """Register custom CLI commands with the Flask application.

    Args:
        app: Target Flask application instance.
    """
    app.cli.add_command(db_check_command)
    app.cli.add_command(load_curriculum_command)
