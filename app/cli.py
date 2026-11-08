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


@click.command("load-notes")
@click.option(
    "--notes-dir",
    default="data/notes",
    help="Directory containing markdown study notes organized by subject (default: data/notes).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Validate and stage note contents without committing to the database.",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Force overwrite of topic study notes even if content_reviewed is True in database.",
)
@with_appcontext
def load_notes_command(notes_dir: str, dry_run: bool, force: bool) -> None:
    """Validate, parse, and idempotently ingest Markdown study notes."""
    from app.services.notes_loader import (
        NotesLoader,
        NotesValidationError,
        MissingNotesDirectoryError,
    )

    try:
        loader = NotesLoader(notes_dir=notes_dir, force=force)
        summary = loader.load(dry_run=dry_run)
        click.echo(summary.format_cli_output())
    except MissingNotesDirectoryError as err:
        click.echo(f"Error: {err}", err=True)
        sys.exit(1)
    except NotesValidationError as err:
        click.echo(f"Error: {err}", err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(f"Notes ingestion failed unexpectedly: {exc}", err=True)
        sys.exit(1)


@click.command("load-resources")
@click.option(
    "--data-dir",
    default="data",
    help="Directory containing resources.csv (default: data).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Validate resources without saving them.",
)
@with_appcontext
def load_resources_command(data_dir: str, dry_run: bool) -> None:
    """Idempotently load curated Semester 5 topic resource links."""
    from app.services.resource_loader import (
        ResourceLoader,
        ResourceLoaderError,
    )

    try:
        summary = ResourceLoader(data_dir=data_dir).load(dry_run=dry_run)
    except ResourceLoaderError as err:
        raise click.ClickException(str(err)) from err
    status = "validated (dry run)" if dry_run else "committed"
    click.echo(
        f"Resources {status}: {summary.links_processed} links processed, "
        f"{summary.links_added} added, {summary.links_unchanged} unchanged."
    )


@click.command("notes-status")
@with_appcontext
def notes_status_command() -> None:
    """Display curriculum study notes inventory, review progress, and authoring source distribution."""
    from app.services.notes_loader import get_notes_status

    try:
        status = get_notes_status()
        click.echo(status.format_cli_output())
    except Exception as exc:
        click.echo(f"Failed to query notes status: {exc}", err=True)
        sys.exit(1)


@click.command("setup-local-db")
@click.option(
    "--data-dir",
    default="data",
    help="Directory containing the 4 curriculum CSV files (default: data).",
)
@click.option(
    "--notes-dir",
    default="data/notes",
    help="Directory containing markdown study notes organized by subject (default: data/notes).",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Force overwrite of topic study notes even if content_reviewed is True in database.",
)
@with_appcontext
def setup_local_db_command(data_dir: str, notes_dir: str, force: bool) -> None:
    """Initialize local SQLite database, prepare schema, and ingest curriculum and study notes."""
    uri: str = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    dialect_name: str = db.engine.dialect.name

    if dialect_name != "sqlite" or not uri.startswith("sqlite"):
        if dialect_name == "postgresql" or uri.startswith(("postgresql", "postgres")):
            click.echo(
                "Error: setup-local-db is restricted to local SQLite databases. "
                "Refusing to run against PostgreSQL database.",
                err=True,
            )
        else:
            click.echo(
                "Error: setup-local-db is restricted to local SQLite databases. "
                f"Active database is '{mask_database_uri(uri)}'. Refusing to run.",
                err=True,
            )
        sys.exit(1)

    click.echo("=" * 60)
    click.echo(" StudySphere Local SQLite Database Setup")
    click.echo("=" * 60)
    click.echo(f"> Target Database : {mask_database_uri(uri)}")
    click.echo("-" * 60)

    # 1. Schema preparation via migrations or create_all fallback
    click.echo("[1/3] Preparing database schema...", nl=False)
    try:
        inspector = inspect(db.engine)
        table_names = set(inspector.get_table_names())
        if "alembic_version" in table_names or not table_names:
            from flask_migrate import upgrade
            upgrade()
        else:
            db.create_all()
        click.echo(" OK")
    except Exception as exc:
        click.echo(" FAILED")
        click.echo(f"Error: Failed to prepare database schema: {exc}", err=True)
        sys.exit(1)

    # 2. Ingest curriculum dataset
    click.echo("[2/3] Ingesting curriculum (courses, topics, prerequisites)...")
    from app.services.curriculum_loader import (
        CurriculumLoader,
        CurriculumValidationError,
        MissingDataFileError,
    )

    try:
        curriculum_loader = CurriculumLoader(data_dir=data_dir)
        curriculum_summary = curriculum_loader.load(dry_run=False)
        click.echo(
            f"      Processed {curriculum_summary.courses_count} courses, "
            f"{curriculum_summary.topics_count} topics, "
            f"{curriculum_summary.course_prerequisites_count} course prerequisites, "
            f"{curriculum_summary.topic_prerequisites_count} topic prerequisites."
        )
    except (MissingDataFileError, CurriculumValidationError) as err:
        click.echo(f"Error: {err}", err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(f"Curriculum ingestion failed unexpectedly: {exc}", err=True)
        sys.exit(1)

    # 3. Ingest study notes
    click.echo("[3/3] Ingesting study notes...")
    from app.services.notes_loader import (
        NotesLoader,
        NotesValidationError,
        MissingNotesDirectoryError,
    )

    try:
        notes_loader = NotesLoader(notes_dir=notes_dir, force=force)
        notes_summary = notes_loader.load(dry_run=False)
        click.echo(
            f"      Processed {notes_summary.total_files} note files "
            f"({notes_summary.updated} updated, {notes_summary.unchanged} unchanged, "
            f"{notes_summary.skipped} skipped)."
        )
    except (MissingNotesDirectoryError, NotesValidationError) as err:
        click.echo(f"Error: {err}", err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(f"Notes ingestion failed unexpectedly: {exc}", err=True)
        sys.exit(1)

    # 4. Verify entities
    from app.models.course import Course
    from app.models.topic import Topic

    courses_count: int = Course.query.count()
    topics_count: int = Topic.query.count()
    notes_count: int = Topic.query.filter(
        Topic.content.isnot(None), Topic.content != ""
    ).count()

    click.echo("=" * 60)
    click.echo(" Local SQLite database setup completed successfully!")
    click.echo(
        f"> Total Courses : {courses_count} "
        f"(expected: {curriculum_summary.courses_count})"
    )
    click.echo(
        f"> Total Topics  : {topics_count} "
        f"(expected: {curriculum_summary.topics_count})"
    )
    click.echo(
        f"> Total Notes   : {notes_count} (expected: {notes_summary.total_files})"
    )
    click.echo("=" * 60)


@click.command("load-questions")
@click.option(
    "--file",
    "csv_file",
    default="data/questions.csv",
    help="Path to questions CSV file (default: data/questions.csv).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Validate and stage data in a rolled-back transaction without saving.",
)
@with_appcontext
def load_questions_command(csv_file: str, dry_run: bool) -> None:
    """Validate, parse, and idempotently ingest assessment questions from CSV."""
    from app.services.question_loader import (
        QuestionLoader,
        QuestionsValidationError,
        MissingQuestionsFileError,
    )

    try:
        loader = QuestionLoader(file_path=csv_file)
        summary = loader.load(dry_run=dry_run)
        click.echo(summary.format_cli_output())
    except MissingQuestionsFileError as err:
        click.echo(f"Error: {err}", err=True)
        sys.exit(1)
    except QuestionsValidationError as err:
        click.echo(f"Error: {err}", err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(f"Questions ingestion failed unexpectedly: {exc}", err=True)
        sys.exit(1)


@click.command("train-label-model")
@click.option(
    "--seed",
    default=42,
    type=int,
    help="Random seed for synthetic data generation and holdout split (default: 42).",
)
@click.option(
    "--n-samples",
    default=1000,
    type=int,
    help="Number of synthetic topic histories (default: 1000).",
)
@with_appcontext
def train_label_model_command(seed: int, n_samples: int) -> None:
    """Train the aggregate topic mastery classifier and save evaluation artifacts."""
    from ml.label_model import (
        LABELS,
        generate_synthetic_topic_dataset,
        train_topic_model,
    )

    click.echo("=" * 65)
    click.echo(
        f" Training Topic Mastery Decision Tree (n={n_samples}, seed={seed})"
    )
    click.echo("=" * 65)

    dataset = generate_synthetic_topic_dataset(n=n_samples, seed=seed)
    result = train_topic_model(dataset=dataset, seed=seed)

    click.echo(f"\nModel Parameters     : {result['best_params']}")
    click.echo(f"Training Accuracy    : {result['train_accuracy']:.4f}")
    click.echo(f"Holdout Test Accuracy: {result['test_accuracy']:.4f}")
    diff = result["train_accuracy"] - result["test_accuracy"]
    click.echo(f"Generalization Gap   : {diff:.4f} (transparent overfitting check)")

    click.echo("\n--- Classification Report (Holdout Test Split) ---")
    click.echo(result["classification_report_str"])

    click.echo("--- Confusion Matrix (Labels: Weak, Good, Better, Excellent) ---")
    cm = result["confusion_matrix"]
    click.echo(f"{'Actual \\ Predicted':<20} {'Weak':>8} {'Good':>8} {'Better':>8} {'Excellent':>8}")
    for idx, label in enumerate(LABELS):
        row = cm[idx]
        click.echo(f"{label:<20} {row[0]:>8} {row[1]:>8} {row[2]:>8} {row[3]:>8}")

    click.echo("\n--- Feature Importances ---")
    for feat, imp in result["feature_importances"].items():
        click.echo(f"  * {feat:<22}: {imp:.4f}")

    click.echo("\n--- Persisted Artifacts ---")
    click.echo(f"  * Model artifact   : {result['model_path']}")
    click.echo(f"  * Metrics JSON     : {result['metrics_path']}")
    click.echo(f"  * Tree text export : {result['tree_path']}")
    click.echo("=" * 65)
    click.echo(" Model training completed successfully!")


@click.command("label-attempts")
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Force re-labeling all attempts, including previously labeled records.",
)
@with_appcontext
def label_attempts_command(force: bool) -> None:
    """Recompute per-attempt History labels without changing aggregate topic labels."""
    from app.models.attempt import Attempt
    from app.services.label_service import label_attempt_record

    query = Attempt.query.order_by(Attempt.id.asc())
    if not force:
        query = query.filter(Attempt.label.is_(None))

    attempts_to_label = query.all()
    total = len(attempts_to_label)

    if total == 0:
        click.echo("No attempts require labeling. All attempts already have mastery labels.")
        return

    click.echo(f"Found {total} attempt(s) to classify...")
    labeled_counts: dict[str, int] = {}

    for attempt in attempts_to_label:
        label = label_attempt_record(attempt, commit=False)
        val = label.value
        labeled_counts[val] = labeled_counts.get(val, 0) + 1

    db.session.commit()

    click.echo(f"Successfully labeled {total} attempt(s):")
    for val, count in sorted(labeled_counts.items()):
        click.echo(f"  - {val}: {count}")


@click.command("llm-check")
@with_appcontext
def llm_check_command() -> None:
    """Diagnose LLM provider connectivity, probe model latency, and check response status."""
    import time
    from app.services.llm_client import get_llm_client, sanitize_text

    provider: str = (current_app.config.get("LLM_PROVIDER") or "gemini").strip()
    model: str = (
        current_app.config.get("GEMINI_MODEL") or "gemini-3.5-flash-lite"
    ).strip()
    api_key: str | None = current_app.config.get("GEMINI_API_KEY")

    click.echo(f"Provider: {provider}")
    click.echo(f"Model: {model}")

    if provider.lower() == "fake":
        click.echo("fake provider, no network call")
        return

    prompt = "Say hi in 3 words"
    client = get_llm_client(provider=provider, model=model)
    start_time = time.perf_counter()

    try:
        resp = client.generate(prompt)
        elapsed = time.perf_counter() - start_time
        click.echo("HTTP status: 200")
        click.echo(f"Time: {elapsed:.2f}s")
        click.echo(f"Response: {sanitize_text(resp.strip()[:100], api_key)}")
    except Exception as err:
        elapsed = time.perf_counter() - start_time
        err_type = type(err).__name__
        sanitized_msg = sanitize_text(str(err), api_key)
        click.echo(f"Error type: {err_type}")
        click.echo(f"Time: {elapsed:.2f}s")
        click.echo(f"Details: {sanitized_msg}")


@click.command("chat-check")
@click.option("--topic-id", required=True, type=int, help="Topic note to use.")
@click.argument("message")
@with_appcontext
def chat_check_command(topic_id: int, message: str) -> None:
    """Run one live chat request against a topic without saving chat history."""
    from app.models.topic import Topic
    from app.services.chat_service import (
        ChatGenerationError,
        ChatInputError,
        generate_chat_answer,
    )

    topic = db.session.get(Topic, topic_id)
    if topic is None:
        raise click.ClickException(f"Topic {topic_id} was not found.")

    try:
        answer = generate_chat_answer(
            message,
            topic.content or "",
            topic_title=topic.name,
            subject=topic.subject,
        )
    except ChatInputError as err:
        raise click.BadParameter(str(err), param_hint="message") from err
    except ChatGenerationError as err:
        from app.services.llm_client import sanitize_text

        cause = err.__cause__
        if cause is not None:
            error_type = type(cause).__name__
            error_message = sanitize_text(
                str(cause),
                current_app.config.get("GEMINI_API_KEY"),
            )
        else:
            error_type = type(err).__name__
            error_message = str(err)

        click.echo(f"Chat failure type: {error_type}", err=True)
        click.echo(f"Chat failure: {error_message}", err=True)
        if err.raw_response is not None:
            raw_response = sanitize_text(
                err.raw_response,
                current_app.config.get("GEMINI_API_KEY"),
            )
            click.echo("Raw model reply:", err=True)
            click.echo(raw_response, err=True)
        else:
            click.echo("Raw model reply: unavailable.", err=True)
        raise click.ClickException("Chat generation failed.") from err
    click.echo(answer)


def register_cli_commands(app: Flask) -> None:
    """Register custom CLI commands with the Flask application.

    Args:
        app: Target Flask application instance.
    """
    app.cli.add_command(db_check_command)
    app.cli.add_command(load_curriculum_command)
    app.cli.add_command(load_notes_command)
    app.cli.add_command(load_resources_command)
    app.cli.add_command(notes_status_command)
    app.cli.add_command(setup_local_db_command)
    app.cli.add_command(load_questions_command)
    app.cli.add_command(train_label_model_command)
    app.cli.add_command(label_attempts_command)
    app.cli.add_command(llm_check_command)
    app.cli.add_command(chat_check_command)
