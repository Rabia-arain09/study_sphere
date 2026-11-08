---
title: StudySphere
sdk: docker
app_port: 7860
---

# StudySphere 🎓

StudySphere is a production-grade, adaptive ML-based personalized study platform. Students navigate through their curriculum hierarchically (**Semester &rarr; Course &rarr; Topic**), complete topic-specific quizzes, and receive automated mastery assessments powered by a **scikit-learn Decision Tree classifier** that categorizes topic mastery into four performance tiers: **Weak**, **Good**, **Better**, or **Excellent**.

When foundational deficits are detected, StudySphere performs **prerequisite-based knowledge gap analysis** across curriculum concept dependency graphs. Additionally, students can upload unstructured study materials (raw text, document images, or web URLs) to extract concepts via OCR and automatically synthesize summaries and calibrated questions via LLM pipelines. Authoritative Markdown lecture notes stored directly on topics serve as the pedagogical ground truth.

---

## Architecture Overview

```mermaid
flowchart TD
    subgraph Client["Presentation & Client Layer"]
        UI["Web Browser / Client UI"]
        AuthBP["Auth Blueprint (/auth)"]
        TopicsBP["Topics Blueprint (/topics)"]
        QuizBP["Quiz Blueprint (/quiz)"]
        UploadBP["Upload Blueprint (/upload)"]
        DashBP["Dashboard Blueprint (/dashboard)"]
    end

    subgraph Core["Flask Application Core (app/)"]
        Factory["create_app() Factory"]
        Extensions["Extensions (SQLAlchemy + Migrate)"]
        Config["Config (Dev / Test / Prod)"]
        CLI["CLI Commands (db-check, load-curriculum)"]
    end

    subgraph Services["Service & Domain Logic (app/services/)"]
        CurriculumLoader["Curriculum Loader & Validator (DAG)"]
        GapAnalysis["Knowledge Gap Graph Traversal (DAG)"]
        QuizEngine["Scoring & Evaluation Engine"]
        IngestionService["OCR & LLM Synthesis Pipeline"]
    end

    subgraph ML["Machine Learning Pipeline (ml/)"]
        DTClassifier["Decision Tree Mastery Classifier (4-Level)"]
        FeatureExtractor["Feature Vector Preprocessor"]
        ModelStorage["Joblib Model Artifacts"]
    end

    subgraph DB["Persistence Layer (SQLAlchemy ORM + Supabase PostgreSQL)"]
        CoursesTbl[("courses")]
        CoursePrereqsTbl[("course_prerequisites")]
        UsersTbl[("users")]
        TopicsTbl[("topics (with notes & content)")]
        PrereqsTbl[("prerequisites")]
        ResourcesTbl[("resources")]
        QuestionsTbl[("questions")]
        AttemptsTbl[("attempts (Weak / Good / Better / Excellent)")]
    end

    UI --> AuthBP & TopicsBP & QuizBP & UploadBP & DashBP
    AuthBP & TopicsBP & QuizBP & UploadBP & DashBP --> Factory
    Factory --> Extensions & Config & CLI
    CLI --> CurriculumLoader
    CurriculumLoader --> CoursesTbl & CoursePrereqsTbl & TopicsTbl & PrereqsTbl
    QuizBP --> QuizEngine
    UploadBP --> IngestionService
    DashBP --> GapAnalysis
    QuizEngine --> FeatureExtractor --> DTClassifier
    DTClassifier --> ModelStorage
    GapAnalysis --> PrereqsTbl & CoursePrereqsTbl
    Extensions --> DB
    Services --> DB
```

---

## Folder Structure

```text
study_sphere/
├── app/
│   ├── __init__.py          # create_app application factory & route registration
│   ├── cli.py               # Custom CLI commands (db-check, load-curriculum, load-notes, notes-status, setup-local-db)
│   ├── config.py            # Development, Testing, Production configurations & DB fallback
│   ├── extensions.py        # SQLAlchemy & Flask-Migrate extension singletons
│   ├── blueprints/          # Modular domain-driven route handlers
│   │   ├── __init__.py      # Blueprint package exporter
│   │   ├── auth/            # Authentication, session, and student registration
│   │   ├── topics/          # Semester > Course > Topic browsing & syllabus tree
│   │   ├── quiz/            # Quiz sessions, answer evaluation, and attempt recording
│   │   ├── upload/          # Multimodal ingestion (OCR text/image/URL)
│   │   └── dashboard/       # Knowledge gap visualization & mastery analytics
│   ├── models/              # Relational models with ML pipeline docstrings
│   │   ├── __init__.py      # Model registry exporter
│   │   ├── user.py          # User authentication and cohort profile
│   │   ├── course.py        # Course & CoursePrerequisite models with cascading constraints
│   │   ├── topic.py         # Curriculum nodes with course_id, Markdown notes & difficulty
│   │   ├── prerequisite.py  # Directed knowledge graph edges & self-reference checks
│   │   ├── resource.py      # Targeted remediation media (notes, diagrams, links)
│   │   ├── question.py      # Assessment bank items (curriculum & OCR/LLM generated)
│   │   └── attempt.py       # Attempt logs & 4-tier Decision Tree mastery labels
│   ├── services/            # Domain logic (curriculum loader, notes loader, DAG gap analysis)
│   │   ├── __init__.py
│   │   ├── curriculum_loader.py # Multi-CSV validation, DAG cycle detection & upsert
│   │   └── notes_loader.py  # Front-matter validation, markdown note ingestion & status aggregation
│   ├── static/              # Frontend static assets
│   │   ├── css/main.css
│   │   ├── js/main.js
│   │   └── img/
│   └── templates/           # Jinja2 presentation templates
│       └── base.html
├── data/                    # Curriculum dataset benchmarks & study notes
│   ├── courses.csv              # 44 degree courses (code, title, domain, credits, contact)
│   ├── course_prerequisites.csv # 12 course-level academic prerequisites
│   ├── topics.csv               # Syllabus topics with tags, difficulty & week
│   ├── topic_prerequisites.csv  # Directed topic-level concept prerequisites
│   ├── questions.csv            # Calibrated assessment items (mcq, tf, short, theory)
│   └── notes/                   # Markdown study notes organized by subject-slug/NN-topic-slug.md
├── migrations/              # Alembic / Flask-Migrate migration scripts
│   ├── versions/            # Versioned migration revision files
│   │   ├── fe0300e0055e_initial_migration.py
│   │   ├── 856dc8c30709_enable_row_level_security.py
│   │   └── ea3d4269939c_course_model_notes_columns_4level_labels.py
│   └── env.py
├── ml/                      # Scikit-learn pipelines, Decision Tree trainer & inference
│   └── __init__.py
├── tests/                   # Pytest automated test suite
│   ├── __init__.py
│   ├── conftest.py          # App and test fixtures
│   ├── test_config.py       # Configuration and URI masking tests
│   ├── test_curriculum_loader.py # Loader validations, cycles, idempotency & real CSVs
│   ├── test_factory.py      # App factory and health checks
│   ├── test_models.py       # Model constraints, foreign keys, and relationships
│   ├── test_notes_loader.py # Notes parser, validation rules, idempotency & CLI tests
│   └── test_setup_local_db.py # Local SQLite setup CLI, idempotency & PostgreSQL guard tests
├── .env.example             # Environment variable template (no secrets)
├── .gitignore               # Strict ignore rules for Python, venv, caches, DBs, and models
├── requirements.txt         # Pinned production and development dependencies
├── render.yaml              # Render build, start, and environment configuration
├── scripts/ensure_models.py # Build-time trainer for missing Decision Tree artifacts
├── run.py                   # Application entry point for local development
├── wsgi.py                   # Production Gunicorn entry point
└── README.md                # Project documentation and developer guide
```

---

## Setup & Installation

### 1. Prerequisites
- Python 3.11, 3.12, 3.13, or 3.14
- Git

### 2. Clone Repository & Setup Virtual Environment
```bash
git clone https://github.com/Rabia-arain09/study_sphere.git
cd study_sphere

# Create virtual environment
python -m venv venv

# Activate on Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Activate on Linux / macOS
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy the template to `.env`:
```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```
Update `.env` as required:
- Leave `DATABASE_URL` blank or set to `sqlite:///instance/studysphere.db` for local SQLite development.
- For Supabase/PostgreSQL production deployment, provide the connection string:
  ```env
  DATABASE_URL=postgresql+psycopg2://postgres.your-project-ref:your-url-encoded-password@aws-0-your-region.pooler.supabase.com:5432/postgres?sslmode=require
  ```
- Configure `SECRET_KEY` and optional `LLM_API_KEY`.

---

## Deploy on Render

Render uses [render.yaml](./render.yaml) to install dependencies, create any missing
Decision Tree artifacts, and run the production WSGI application with Gunicorn. The
production factory requires `SECRET_KEY` and `DATABASE_URL`; configure an LLM key to
enable AI-powered uploads.

Required environment variable names:
- `SECRET_KEY`
- `DATABASE_URL`
- `GEMINI_API_KEY` or `LLM_API_KEY`

After deployment, apply database migrations with:
```bash
flask --app wsgi db upgrade
```

The application health check remains available at `/health`.

---

## Deploy on Hugging Face Spaces

1. Create a new Space and select **Docker** as its SDK.
2. Push this repository to the Space, including the root `Dockerfile` and this README.
3. In the Space's **Settings**, add the following names under **Variables and secrets**
   (store credentials as secrets):
   - `SECRET_KEY`
   - `DATABASE_URL`
   - `GEMINI_API_KEY`
   - `LLM_PROVIDER`
   - `GEMINI_MODEL`
4. Wait for the Docker image to build and the Space to start. The app listens on port
   `7860`; check `/health` to verify it is responding.

---

## Supabase Setup for Teammates

Follow these steps to connect your local development environment to the shared Supabase PostgreSQL instance:

1. **Copy the Environment Template**:
   ```bash
   cp .env.example .env    # On Windows: copy .env.example .env
   ```
2. **Use the Session Pooler (IPv4 Compatible)**:
   - In the Supabase Dashboard, navigate to **Project Settings &rarr; Database &rarr; Connection Pooling**.
   - Select **Mode: Session** on port **5432**.
   - **Do NOT use the direct connection string** (`db.<project-ref>.supabase.co`), because direct hosts only resolve to IPv6 on some ISPs/networks, causing DNS resolution failures (`Name or service not known`) on IPv4 connections.
   - The connection format is:
     ```env
     DATABASE_URL=postgresql+psycopg2://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require
     ```
3. **URL-Encode Special Characters in Your Password**:
   - If your database password contains characters like `@`, `:`, `/`, `?`, `#`, `[`, `]`, `%`, `+`, or `&`, they **MUST** be percent-encoded (URL-encoded) before pasting into `.env`.
   - Quick one-liner to encode your password:
     ```bash
     python -c "import urllib.parse; print(urllib.parse.quote_plus('your_password_here'))"
     ```
   - Common replacements: `@` &rarr; `%40`, `#` &rarr; `%23`, `+` &rarr; `%2B`, `%` &rarr; `%25`, `/` &rarr; `%2F`.
4. **Never Commit Secrets**:
   - Never commit `.env` or any file containing plaintext credentials. `.env` is listed in `.gitignore` and must remain strictly local.
5. **Free Tier Inactivity Auto-Pause**:
   - Supabase free-tier projects automatically pause after 7 consecutive days of inactivity.
   - If `db-check` reports connection timeouts or refused connections, log in to [Supabase Dashboard](https://supabase.com/dashboard) and click **Restore project** (takes ~1-2 minutes).
6. **Verify Connection**:
   - Run the diagnostic probe to confirm connectivity, table inventory, and transactional rollback:
     ```bash
     flask --app run.py db-check
     ```

---

## Local SQLite Development Setup (Fast Local Workflow)

Supabase PostgreSQL queries from regions with high network latency (e.g., Pakistan) can incur ~400 ms per round trip, which slows down iterative feature development. For high-speed local development, StudySphere supports an automated local SQLite workflow where queries execute in sub-millisecond time and all browsing routes respond in under 120 ms.

### 1. Initialize Local SQLite Database (`setup-local-db`)

The `setup-local-db` command prepares the schema (applying migrations or `create_all`), ingests the curriculum dataset, and populates every study note. Course, topic, and note totals follow the current repository data. It is strictly idempotent and refuses to run against PostgreSQL databases.

Run in PowerShell:
```powershell
# Option A: In-session environment override (recommended; leaves .env untouched)
$env:DATABASE_URL = "sqlite:///instance/studysphere.db"
flask --app run.py setup-local-db

# Option B: Using .env configuration (when DATABASE_URL is set to SQLite in .env)
flask --app run.py setup-local-db
```

Example output:
```text
============================================================
 StudySphere Local SQLite Database Setup
============================================================
> Target Database : sqlite:///.../instance/studysphere.db
------------------------------------------------------------
[1/3] Preparing database schema... OK
[2/3] Ingesting curriculum (courses, topics, prerequisites)...
      Processed <course-count> courses, <topic-count> topics, <course-prerequisite-count> course prerequisites, <topic-prerequisite-count> topic prerequisites.
[3/3] Ingesting study notes...
      Processed <note-count> note files (<updated-count> updated, 0 unchanged, 0 skipped).
============================================================
 Local SQLite database setup completed successfully!
> Total Courses : <course-count> (expected: <course-count>)
> Total Topics  : <topic-count> (expected: <topic-count>)
> Total Notes   : <note-count> (expected: <note-count>)
============================================================
```

### 2. Running the App Locally on SQLite

#### Method 1: Using PowerShell Environment Variable (Session-Scoped)
Run with an in-session override without modifying `.env`:
```powershell
# Set SQLite database URL for current PowerShell session
$env:DATABASE_URL = "sqlite:///instance/studysphere.db"

# Start the Flask development server
python run.py
```

#### Method 2: Using `.env` (Persistent)
Edit `.env` and set `DATABASE_URL` to local SQLite:
```env
DATABASE_URL=sqlite:///instance/studysphere.db
```
Then start the server:
```powershell
python run.py
```

### 3. Switching Back to Supabase

To switch back to Supabase PostgreSQL:

#### If using PowerShell session override:
Clear the environment variable to revert to `.env`:
```powershell
# Remove the environment variable override to revert to .env
Remove-Item Env:\DATABASE_URL

# Verify connection to Supabase
flask --app run.py db-check
```

#### If using `.env`:
Restore your Supabase connection string in `.env`:
```env
DATABASE_URL=postgresql+psycopg2://postgres.<project-ref>:<url-encoded-password>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require
```
Verify connectivity:
```powershell
flask --app run.py db-check
```

---

## Database Migrations & Curriculum Ingestion

### 1. Apply Database Migrations
Generate and upgrade tables using Flask-Migrate:
```bash
flask --app run.py db upgrade
```

> **Supabase Migration Notice**:
> Revision `b4f8a1e2c9d0` (`b4f8a1e2c9d0_add_attempt_answers_and_theory_self_rating.py`) introduces the `attempt_answers` table with cascading foreign keys (`attempt_id`, `question_id`), index on `attempt_id`, unique compound constraint `(attempt_id, question_id)`, theory `self_rating` check constraint, PostgreSQL Row Level Security (RLS), and alters `attempts.wrong_count` to `Float`. This migration has been applied locally on SQLite and **must be applied to Supabase PostgreSQL later using the existing migration workflow** (`flask --app run.py db upgrade`).

### 2. Curriculum Data Files (`data/`)
StudySphere ingests curriculum content from four relational CSV files located in `data/` (encoded with `utf-8-sig`):
- `courses.csv`: Defines accredited degree courses (`semester`, `course_code`, `title`, `domain`, `credit_hours`, `contact_hours`, `is_elective`).
- `course_prerequisites.csv`: Declares macro course-level dependencies (`course_code`, `prerequisite_code`).
- `topics.csv`: Contains topic syllabus concepts linked to courses by title (`semester`, `subject`, `course_code`, `week`, `topic`, `difficulty`, `tags`, `description`).
- `topic_prerequisites.csv`: Maps directed topic concept dependencies (`subject`, `topic`, `prerequisite_subject`, `prerequisite_topic`).

### 3. Curriculum Loader CLI
Ingest curriculum datasets using the custom CLI command:
```bash
# Validate and ingest into the configured database (SQLite or Supabase PostgreSQL)
flask --app run.py load-curriculum --data-dir data

# Dry-run validation without writing to the database
flask --app run.py load-curriculum --data-dir data --dry-run
```

**Key Features of the Curriculum Loader**:
- **Strict Pre-Write Validation**: Verifies file existence, required column headers, integer difficulty ranges (1–5), no duplicate topic names within subjects, referential integrity across courses and topics, absence of self-dependencies, and directed acyclic graph (DAG) cycle detection using depth-first search.
- **Fail-Fast Safety**: If any validation rule fails, detailed error messages are printed and the process terminates non-zero without writing any data.
- **Transactional Idempotency**: Executes inside a single database transaction using natural keys (`Course.code`, `CoursePrerequisite.(course_id, prerequisite_course_id)`, `Topic.(semester, subject, name)`, `Prerequisite.(topic_id, prerequisite_topic_id)`). Running the loader repeatedly updates attributes without duplicating rows.
- **Summary Reporting**: Displays an execution summary table detailing total rows processed per table.

### 4. Study Notes Management & Ingestion

StudySphere stores authoritative Markdown study notes directly on curriculum topics in the database (`Topic.content`). These notes serve as pedagogical ground truth for automated question generation and targeted student remediation.

#### Notes Folder Convention
Notes are stored on the filesystem organized by subject slug:
```text
data/notes/<subject-slug>/NN-topic-slug.md
```
Each note file begins with YAML front matter enclosed by `---` delimiters, followed by the Markdown body:
```markdown
---
subject: Machine Learning
topic: "Introduction to Machine Learning"
semester: 5
week: "1"
difficulty: 1
content_source: ai_generated
content_reviewed: false
---

# Introduction to Machine Learning
*Machine Learning · Semester 5 · Week 1 · Difficulty 1/5*

**Key concept:** Machine learning lets a computer learn patterns from data...
```

**Required Front Matter Keys**:
- `subject`: Exact subject name matching curriculum syllabus (e.g., `Machine Learning`).
- `topic`: Exact topic name matching `Topic.name` in database.
- `semester`: Academic semester integer (1–8).
- `week`: Syllabus schedule string (e.g., `"1"`, `"2-3"`).
- `difficulty`: Complexity rating (1–5).
- `content_source`: Authoring source enum: strictly `lecture` or `ai_generated`.
- `content_reviewed`: Boolean review indicator (`true` or `false`).

#### Ingesting Study Notes (`load-notes`)
Ingest note files into the configured database (SQLite or Supabase PostgreSQL):
```bash
# Ingest all notes from default data/notes
flask --app run.py load-notes

# Specify a custom notes directory
flask --app run.py load-notes --notes-dir data/notes

# Dry-run validation (validates files and stages changes without saving)
flask --app run.py load-notes --dry-run

# Force overwrite of previously reviewed topics
flask --app run.py load-notes --force
```

**Key Features of the Notes Loader**:
- **Comprehensive Pre-Write Validation**: Prior to opening database write operations, all note files are parsed and validated for required YAML keys, allowed `content_source` values (`lecture`, `ai_generated`), non-empty markdown bodies, absence of duplicate notes targeting the same `(semester, subject, topic)` key, and referential integrity against existing database topics.
- **Fail-Fast Transactional Safety**: If any file fails validation or if the notes directory is missing, human-readable errors identify the offending files, the command exits with non-zero status, and nothing is written to the database.
- **Strict Idempotency**: Executes in a single database transaction, updating records only when content, authoring source, or review status differs from current database values.
- **Review Protection**: To prevent unreviewed notes from overwriting instructor-vetted content, topics where `content_reviewed` is already `true` in the database are safely skipped unless `--force` is explicitly provided.
- **Execution Summary**: Outputs total files inspected, updated count, unchanged count, and skipped count.

#### How Teammates Mark a Note as Reviewed
1. Open the relevant Markdown note file (e.g., `data/notes/machine-learning/01-introduction-to-machine-learning.md`).
2. Verify the pedagogical quality of the Markdown body.
3. Update the YAML front matter to set:
   ```yaml
   content_reviewed: true
   ```
4. Ingest and persist the reviewed status into the database using the `--force` flag:
   ```bash
   flask --app run.py load-notes --force
   ```

#### Inspecting Notes Inventory & Progress (`notes-status`)
Check syllabus study notes coverage and authoring distribution across curriculum subjects:
```bash
flask --app run.py notes-status
```
Example Output:
```text
====================================================================================
 StudySphere Study Notes Status
====================================================================================
Subject                      Total Topics  With Notes   Reviewed  AI Generated  Lecture
------------------------------------------------------------------------------------
Compiler Construction                  32          32          0            32        0
Machine Learning                       48          48          0            40        8
Operating Systems                      37          37          0            37        0
Web Engineering                        48          48          0            48        0
------------------------------------------------------------------------------------
Total                                 165         165          0           157        8
====================================================================================
```

### 5. Assessment Questions & Question Loader CLI (`data/questions.csv`)

StudySphere supports calibrated topic assessments evaluating student mastery across four question formats: Multiple Choice (`mcq`), True/False (`tf`), Short Answer (`short`), and Conceptual/Theory (`theory`).

#### Questions CSV Schema
Question assessment banks are stored in CSV format (encoded with `utf-8-sig`) with the following column structure:

| Column | Type | Description |
| :--- | :--- | :--- |
| `semester` | Integer | Enrolled academic semester (1–8). |
| `subject` | String | Academic subject/course title matching curriculum (e.g., `Machine Learning`). |
| `topic` | String | Specific syllabus topic name matching natural key (e.g., `Introduction to Machine Learning`). |
| `type` | String | Question format: `mcq` (multiple-choice), `tf` (true/false), `short` (text match), or `theory` (conceptual explanation). |
| `question_text`| Text | The prompt or problem statement presented to the learner. |
| `option_a` | Text | Option A text (required for `mcq`; "True" for `tf`; empty for others). |
| `option_b` | Text | Option B text (required for `mcq`; "False" for `tf`; empty for others). |
| `option_c` | Text | Option C text (optional for `mcq`; empty for others). |
| `option_d` | Text | Option D text (optional for `mcq`; empty for others). |
| `correct_answer` | Text | Ground truth: option key (`A`/`B`/`C`/`D`) for `mcq`; `True`/`False` for `tf`; pipe-delimited variants (e.g., `supervised\|supervised learning`) for `short`; instructor reference model answer for `theory`. |
| `source` | String | Provenance origin: `curriculum` (curated) or `generated` (LLM/active learning). |

#### Question Ingestion Commands
Ingest or stage question banks using the custom CLI command:
```bash
# Validate and ingest questions into database
flask --app run.py load-questions --file data/questions.csv

# Dry-run validation (verifies syntax, types, and referential integrity without persisting)
flask --app run.py load-questions --file data/questions.csv --dry-run
```

**Key Features of the Question Loader**:
- **Pre-Write Referential Validation**: Resolves each row's `(semester, subject, topic)` against existing curriculum `Topic` entities before any write operations occur.
- **Fail-Fast Error Reporting**: Accumulates and prints all syntax and referential errors with exact CSV row numbers, terminating immediately on invalid input without partial database writes.
- **Idempotency Guarantee**: Matches existing questions by compound key `(topic_id, type, question_text)`. Re-running the loader updates modified attributes without generating duplicate rows.
- **Scoring Engine Integration**: Multiple-choice matches option keys or values case-insensitively, True/False evaluates case-insensitively, Short Answer matches any `|`-delimited variant after trimming, and Theory questions display instructor model answers while remaining excluded from numerical attempt scoring.

### 6. Run the Application
```bash
python run.py
```
The server will start at `http://127.0.0.1:5000/`. You can verify health at `http://127.0.0.1:5000/health`.

### 7. Run Automated Tests
```bash
pytest -v
```

---

## Database Schema & Models

### 1. New & Updated Entities
- **`Course`** (`courses`):
  - `id`: Integer primary key, autoincrement.
  - `code`: Unique course code (e.g., `CS102`, `CS3xx-E2`).
  - `title`: Unique course title (e.g., `Programming Fundamentals`).
  - `semester`: Integer academic semester (1–8).
  - `domain`: Academic area (`Computing Core`, `General Education`, etc.).
  - `credit_hours`: Integer credit weight (e.g., `3`, `4`).
  - `contact_hours`: Lecture-lab contact string (e.g., `"3-3"`, `"3-0"`).
  - `is_elective`: Boolean flag distinguishing core vs elective courses.
- **`CoursePrerequisite`** (`course_prerequisites`):
  - `course_id` & `prerequisite_course_id`: Foreign keys to `courses.id` (`ON DELETE CASCADE`).
  - Composite primary key and unique constraint.
  - `CHECK (course_id != prerequisite_course_id)` preventing self-prerequisites.
- **`Topic`** (`topics`) updates:
  - `course_id`: Foreign key to `courses.id` (`ON DELETE CASCADE`, not null, indexed).
  - `week`: String representing academic week/schedule (e.g., `"1"`, `"2-3"`, `"11-13"`).
  - `content`: Text holding authoritative study notes in Markdown format.
  - `content_source`: Enum (`lecture`, `ai_generated`, nullable).
  - `content_reviewed`: Boolean tracking instructor/teaching-assistant review.
- **`Attempt.label`** (`attempts`) 4-Tier Enum:
  - Replaced legacy 3-tier labels with: **`Weak`**, **`Good`**, **`Better`**, **`Excellent`**.
  - Seamlessly handles PostgreSQL native enum type replacement (`masterylabel`) and SQLite portability.
- **Row Level Security (RLS)**:
  - Enabled on `courses` and `course_prerequisites` (alongside existing application tables) in PostgreSQL to guard against unauthenticated public REST access.

---

## Team Workflow & Collaboration Rules

To enable 3 developers to work concurrently on `main` without merge conflicts:

1. **Branching Strategy**:
   - `main` branch is protected and always deployable.
   - Each developer works on short-lived feature branches:
     - `feat/developer-name-feature-title`
     - `fix/developer-name-bug-title`
     - `ml/developer-name-model-title`

2. **Modular Ownership**:
   - **Developer 1 (Core & Auth/Topics)**: Focuses on `app/blueprints/auth/`, `app/blueprints/topics/`, and curriculum CRUD.
   - **Developer 2 (Quiz & ML Pipeline)**: Focuses on `app/blueprints/quiz/`, `app/blueprints/dashboard/`, and `ml/` Decision Tree modeling.
   - **Developer 3 (Upload, OCR & LLM)**: Focuses on `app/blueprints/upload/` and `app/services/` ingestion pipelines.

3. **Database Migration Etiquette**:
   - Never manually edit existing applied migration files.
   - Always run `flask --app run.py db migrate -m "descriptive message"` on your branch.
   - Check for multiple Alembic heads before opening a pull request (`flask --app run.py db heads`).
   - If a merge conflict occurs in `migrations/`, run `flask --app run.py db merge heads`.

4. **Pull Requests & Code Quality**:
   - All code must comply with PEP 8 and include type hints (`Mapped`, `mapped_column`, return types).
   - All tests must pass before submitting a PR (`pytest`).
   - Never commit `.env`, `*.db`, `instance/`, `uploads/`, or `*.joblib` files.

---

## Recommender (Content-Based)

StudySphere features a content-based recommendation engine (`ml/recommender.py` and `app/services/recommendation_service.py`) that recommends related curriculum topics to students based on vocabulary overlap, conceptual relevance, and syllabus proximity.

### How It Works (For Viva & Technical Defense)

1. **Text Aggregation & Title Weighting**:
   - Each topic is represented by an aggregated text document formed by repeating the topic **name 3 times** (giving title terms higher term frequency), combined with the topic **description**, **tags**, and the first **~1,500 characters of Markdown lecture notes content**.
   - Standard English stop words (`stop_words="english"`) are removed to eliminate non-informative terms like "the", "is", and "with".

2. **TF-IDF Vectorization (`TfidfVectorizer`)**:
   - **Term Frequency (TF)**: Measures how frequently a word appears in a topic's text. We use `sublinear_tf=True`, which applies logarithmic scaling ($1 + \log(\text{tf})$) instead of raw counts. This prevents long notes or repeatedly used terms from unfairly dominating shorter topics.
   - **Inverse Document Frequency (IDF)**: Measures how unique or informative a word is across the curriculum topics ($\log \frac{N}{\text{df}} + 1$). Common words across topics (like "system" or "introduction") receive low IDF weights, while specialized terms (like "perceptron", "deadlock", "syntax") receive high IDF weights.
   - The result is a high-dimensional sparse numerical vector for each topic.

3. **Cosine Similarity**:
   - Compares the angle between two topic TF-IDF vectors $\mathbf{u}$ and $\mathbf{v}$:
     $$\text{Cosine Similarity}(\mathbf{u}, \mathbf{v}) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|_2 \|\mathbf{v}\|_2}$$
   - Because TF-IDF vectors are L2-normalized, cosine similarity equals the dot product of the two vectors, ranging from **0.0** (orthogonal, zero shared vocabulary) to **1.0** (identical vocabulary distribution).
   - The query topic itself is always excluded, and zero-score candidates (no common vocabulary) are filtered out.

4. **Same-Subject Boost (+0.05)**:
   - When a candidate topic belongs to the same academic subject/course as the query topic and has a positive base similarity score ($\text{sim} > 0$), a small additive boost of **+0.05** (capped at 1.0) is applied.
   - **Why?** Topics within the same subject naturally belong to the same pedagogical module and course timeline, giving students immediate contextual follow-up concepts while still permitting cross-disciplinary discovery (e.g., Compiler Construction linking to Operating Systems linkers/loaders).

5. **In-Memory Caching & Single-Query Retrieval**:
   - The recommender is lazily loaded and fitted once per application process, kept in memory, and only rebuilt if the database state changes (detected via topic count, max topic ID, or content length sum).
   - The related topics endpoint (`GET /topics/<id>/related`) and topic detail view batch target topic verification and recommendation entity fetching into **a single SQL query** (`Topic.id.in_([topic_id] + rec_ids)` with `joinedload(Topic.course)`), achieving **sub-10ms** response times on SQLite.

---

## Design Decisions

- **Complete Quiz Submissions**: Require a non-blank response to every question and preserve the current question set and submitted answers when redirecting students to incomplete quizzes.
- **Accessible Study Chat Drawer**: Keep the existing saved chat and endpoints in a keyboard-accessible drawer, launched from both page content and fixed Ask AI controls.
- **Homepage Study Context**: Reuse the private topic/upload chat routes and saved histories, with authenticated selectors that expose only semester-matched subjects and the current student's uploads.
- **Empty Quiz Submission Handling**: Reject submissions with no non-whitespace answers on both the server and client, without recording an attempt or changing upload quiz statistics.
- **Grounded Study Chat**: Keep topic and upload conversations private per user, save turns for review, enforce a daily question quota, and instruct the existing LLM client to answer only from the displayed study material.
- **Document Upload Extraction**: Accept PDF, PPTX, and DOCX files up to 10 MB, extract text in memory, and include the sanitized filename in duplicate identity so saved materials retain their source name without retaining original files.
- **Course Note Scope**: Use three foundational topics per named course, each with a short note and six generated questions; omit placeholder electives without real course names.
- **Application Factory Pattern**: Adopted `create_app()` factory with modular Blueprint separation (`auth`, `topics`, `quiz`, `upload`, `dashboard`) to isolate developer workflows and eliminate circular dependencies.
- **Dynamic Database Adapter Switching**: Configured `app/config.py` to automatically normalize Supabase `postgres://` or `postgresql://` URIs to `postgresql+psycopg2://` while falling back to zero-config SQLite (`instance/studysphere.db`).
- **Standardized Migration Naming Conventions**: Enforced explicit SQLAlchemy `MetaData` constraint naming convention (`ix_`, `uq_`, `ck_`, `fk_`, `pk_`) in `app/extensions.py` to prevent unnamed constraint errors during SQLite and PostgreSQL migrations.
- **Portability of Enumerations**: Implemented `native_enum=False` on `ResourceType`, `QuestionType`, and `QuestionSource` to maintain identical schema definitions and validation between local SQLite development and Supabase PostgreSQL production.
- **4-Level Mastery Classification**: Transitioned `MasteryLabel` from 3-tier to 4-tier (`Weak`, `Good`, `Better`, `Excellent`) using safe PostgreSQL native enum replacement and SQLite fallback.
- **Hierarchical Course-Topic Relationship**: Introduced normalized `Course` and `CoursePrerequisite` entities to link topics under degree courses and enforce course-level academic prerequisite DAGs.
- **Comprehensive Curriculum Ingestion Pipeline**: Built `curriculum_loader.py` with multi-tier validation, DFS cycle detection, and idempotent transactional upserts over natural keys.
- **Markdown Study Note Content Grounding**: Added `week`, `content` (Markdown), `content_source`, and `content_reviewed` to `Topic` to store authoritative lecture notes for RAG and automated quiz generation.
- **Explicit Prerequisite Association Entity**: Modeled topic prerequisites via a dedicated `Prerequisite` model with `CASCADE` deletions and a `CHECK(topic_id != prerequisite_topic_id)` constraint to enable recursive DAG traversals during knowledge gap analysis.
- **Flexible JSON Payload Storage**: Stored quiz question options (`Question.options`) and topic tags (`Topic.tags`) using standard SQLAlchemy `JSON` types to support polymorphic question structures (MCQ options vs theoretical rubrics) without requiring fragile schema alterations.
- **Decoupled ML Lifecycles**: Isolated scikit-learn models and feature processing under `ml/` and `app/services/` so machine learning training artifacts remain decoupled from web request-response threads.
- **Supabase Session Pooler Engine Optimization**: Configured SQLAlchemy engine options with `pool_pre_ping=True`, `pool_recycle=280` (below the 300s pooler idle timeout), `pool_size=5`, and `max_overflow=2` to eliminate stale pooled connection 500 errors while preserving clean SQLite testing compatibility.
- **Grouped SQL Querying for Curriculum Browsing**: Replaced N+1 lazy queries on `/topics/` and `/topics/semester/<n>` with a single `GROUP BY Topic.course_id` aggregation query, reducing query count from 8 to 2.
- **Course Name Presentation and Chronological Week Grouping**: Standardized template references to display full course names in navigation breadcrumbs, headers, and topic back links ('← Back to <course name> topics') with `Course.name` aliased to `Course.title`, while retaining course codes exclusively as secondary badges on the course page, and grouped syllabus topics in-memory under chronological week headings ('Week X', 'Week X-Y', with unassigned topics under 'Other' at the end) preserving O(1) query complexity and deferred content loading.
- **Deduplication of Related Topics Presentation**: Consolidated related topic recommendations on the topic detail page into a single sidebar list with topic name, course name, and match percentage, eliminating the redundant bottom card grid and purging associated dead CSS.
- **Deferred Content Loading & Eager Relationship Fetching**: Applied `defer(Topic.content)` alongside `selectinload` and `joinedload` on `/topics/course/<id>` and `/topics/<id>`, reducing queries from 77 down to 5 and response time by 94.3% (36.5s to 2.08s).
- **In-Memory Markdown Note Caching**: Implemented `functools.lru_cache` keyed by `(topic_id, content_hash)` in `render_topic_markdown` to eliminate redundant markdown parsing and HTML sanitization on repeat visits.
- **Resilient Global Error Handling & Transaction Rollback**: Implemented friendly 404 and 500 error templates with automatic `db.session.rollback()` and server-side exception logging to prevent poisoned database sessions on failures.
- **Zero-Migration Index Strategy**: Validated that existing indexes (`ix_topics_course_id`, `ix_topics_semester`, `ix_resources_topic_id`, `ix_courses_semester`) already match all query predicates, avoiding redundant migration overhead.
- **PostgreSQL Row Level Security (RLS) Isolation**: Implemented dialect-guarded Alembic migrations that enable RLS across all application tables (`users`, `courses`, `course_prerequisites`, `topics`, `prerequisites`, `resources`, `questions`, `attempts`) to close unauthenticated access via Supabase's public Data API while allowing direct connection roles (`postgres`) full operational access.
- **Diagnostic Database CLI Probe**: Created `flask --app run.py db-check` with masked credentials, version queries, table inventory checks, transactional write/read verification, and automated root-cause guidance for common network, SSL, and authentication failures.
- **Study Notes Cross-Platform Line-Ending Normalization**: Normalized markdown body line endings to `\n` and stripped surrounding whitespace during notes ingestion to guarantee idempotent updates across Windows (CRLF) and Unix (LF) environments.
- **Two-Stage Fail-Fast Notes Ingestion**: Engineered `notes_loader.py` to validate all front-matter headers, source enums, non-empty bodies, topic uniqueness, and database referential integrity before opening a write transaction, ensuring zero partial updates on malformed files.
- **Selective Overwrite Protection with Forced Bypass**: Prevented unreviewed note ingestion from clobbering vetted curriculum content by skipping database records where `content_reviewed` is already `true` unless the `--force` CLI flag is explicitly supplied.
- **Session Authentication & CSRF Protection**: Integrated Flask-Login, Flask-WTF CSRF protection, and Werkzeug password hashing on the `User` model with safe internal redirect validation (`is_safe_url`) to secure student workflows.
- **Sanitized Markdown Notes Reader**: Engineered `render_markdown` using Python-Markdown extensions and `nh3` (Ammonia Rust sanitizer) to safely render AI-generated and lecture notes without XSS vulnerabilities.
- **Hierarchical Curriculum Browsing & Empty States**: Structured student navigation across `/topics/`, `/topics/semester/<n>`, `/topics/course/<id>`, and `/topics/<id>` with week-based ordering, review status badges, prerequisite linking, and friendly 'notes coming soon' empty states.
- **Flask-Login User Loader Scope Isolation**: Explicitly bound the `User` model in `load_user` to eliminate factory instance closure shadowing on `app.models`.
- **Local SQLite Environment & Safe Migration Pipeline**: Built `setup-local-db` CLI command that validates SQLite dialect, runs migrations with `create_all` fallback, loads curriculum CSVs and Markdown notes idempotently, and strictly refuses execution against PostgreSQL.
- **Instance-Relative Path Normalization**: Resolved relative `sqlite:///instance/` URIs in `create_app` against repository root to prevent Flask-SQLAlchemy 3.x from double-nesting paths into `instance/instance/studysphere.db`.
- **TF-IDF Topic Name Repetition Weighting**: Repeated topic name 3 times during document text aggregation in `ml/recommender.py` to give primary title keywords prominent feature weighting above secondary description and body text.
- **Sublinear Term Frequency Scaling**: Configured `sublinear_tf=True` in `TfidfVectorizer` to scale term frequencies logarithmically ($1 + \log(\text{tf})$), dampening the influence of repetitive keywords in detailed lecture notes.
- **Same-Subject Additive Score Boost**: Applied a +0.05 additive boost (capped at 1.0) to candidate topics sharing the same academic subject/course when base cosine similarity is positive, maintaining curriculum cohesion without suppressing genuine cross-course connections.
- **Lazy In-Memory Recommender Lifecycle**: Initialized `TopicRecommender` lazily on first access, cached the fitted instance in memory, and re-fitted automatically only when database state keys (topic count, max ID, or content length checksum) mutate.
- **Batched Single-Query Related Topic Retrieval**: Fetched target topic existence and all top-k recommendation entities in a single database query using `in_([topic_id] + rec_ids)` with eager-loaded `joinedload(Topic.course)`, avoiding N+1 queries and achieving ~4ms response latency.
- **Course Title Fallback for Related Topics**: In `GET /topics/<id>/related` and UI cards, resolved the `course` property from `topic.course.title` falling back to `topic.subject` to provide clear academic subject titles.
- **RESTful 404 on Missing Target in Related Endpoint**: Handled unknown topic IDs in `GET /topics/<id>/related` with HTTP 404 to match `/topics/<id>`, while returning an empty JSON array `[]` for valid topics with zero matching recommendations.
- **Study Notes Reading Time Metric**: Replaced the static 'Pedagogical Ground Truth' header badge with dynamic reading time ('X min read') computed via `calculate_reading_time` at 200 words per minute using `max(1, math.ceil(words / 200))` with a 1-minute minimum for non-empty content and omitting the badge for empty notes.
- **Quiz Engine Attempt Review & Model Reuse**: Reused existing `Question` and `Attempt` database schemas without migrations, persisting student responses in the signed session and recording numeric features (`score`, `total_questions`, `wrong_count`, `attempt_number`, `label=None`) for the Phase 5 Decision Tree.
- **Assessment Ingestion Pipeline and Idempotency**: Built `load-questions` CLI validating CSV headers, natural topic keys, and question type rubrics before transactions, guaranteeing idempotency via `(topic_id, type, question_text)` compound keys.
- **Question Bank Generation & Balanced Option Distribution**: Course question banks use six note-grounded questions per topic (3 MCQ, 1 TF, 1 Short, 1 Theory), balanced MCQ answer positions, and automated CSV schema validation.
- **Tolerant Short-Answer Normalization & Variant Ground Truth**: Normalized short-answer submissions by converting hyphens/underscores to spaces, stripping non-symbol punctuation, collapsing whitespace, and stripping leading articles ('a', 'an', 'the') for strict equality against pipe-delimited variants, while joining accepted answers with ' or ' and eliminating raw '|' delimiters in attempt result reviews.
- **Durable Quiz Answer Persistence & Session Decoupling**: Persisted per-question responses in `attempt_answers` with `(attempt_id, question_id)` unique constraint and cascading foreign keys, reading review data exclusively from the database, and eliminating transient quiz answer payload bloat from signed session cookies.
- **Fractional Scoring & Mathematical Consistency**: Verified `Attempt.score` is already `sa.Float()` in schema and migrated `attempts.wrong_count` to `sa.Float()` so theory self-grading ("Got it" = 1.0 pt, "Partly" = 0.5 pt / 0.5 wrong, "Missed" = 0.0 pt / 1.0 wrong) maintains strict score-wrong-total invariant (`score + wrong_count == total_questions`) without schema bloat.
- **Decision Tree Model Artifact Caching & Zero-Setup Fallback**: Cached the deserialized `label_model.joblib` once per process in `label_service.py`, auto-training and persisting the model with fixed seed=42 if the artifact is missing so teammates and CI environments require zero manual setup.
- **Atomic In-Transaction Mastery Label Assignment**: Assigned `Attempt.label` inside the active database transaction during `submit_quiz` using auto-scored questions, and dynamically recomputed the label in `self-grade` after theory self-ratings update scores, wrong counts, and totals.
- **Indexed Prior Attempt Resolution for Per-Attempt History Labels**: Utilized the compound database index `ix_attempts_user_id_topic_id` (`user_id`, `topic_id`) to derive the previous-score features used by the per-attempt History label.
- **Topic-Level Mastery Aggregation**: Derive each user's topic label from every attempt's average, latest, best, count, and trend features; use this label for dashboard analytics, recommendations, gap analysis, topic pages, and quiz results while preserving per-attempt History labels.
- **Phase 5 Test Assertion Progression**: Upgraded `test_attempt_number_increments_for_same_user_and_topic` to verify that `Attempt.label` is populated with a valid `MasteryLabel` upon quiz submission rather than remaining `None` (which was a Phase 4 placeholder).
- **In-Memory Sequential Delta Calculation**: Computed attempt score percentage changes relative to the prior attempt sequentially in pure Python using `calculate_attempts_history`, eliminating secondary database queries and keeping queries strictly $O(1)$.
- **Compact Sidebar Metric Preservation & Multi-Attempt History Table**: Retained latest attempt summary metrics on the topic sidebar while integrating the 5-attempt table with directional delta arrows and conditional 'View all attempts' links to maintain backward compatibility with existing topic summary checks.
- **Prerequisite Knowledge Gap Graph Traversal**: Engineered pure Python breadth-first search (BFS) traversal (`app/services/gap_analysis.py`) over the topic prerequisite DAG with cycle-safe visited sets, bounded depth (max 4), and constant 4-query retrieval (`joinedload` course, deferred content) prioritizing foundational deficits for personalized student revision.
- **Dashboard Course Progress Chart Real Course Names and Elective Placeholders**: Resolved course names on the progress bar chart from stored database titles, preserving named electives and formatting only generic or unnamed electives as 'Elective N', while wrapping long names and surfacing full names with course codes in interactive tooltips.

---

## Question Bank Authoring, Validation & Ingestion

StudySphere maintains a calibrated assessment question bank for all curriculum topics. Assessment items are organized into subject-specific CSV files under `data/questions/`:

- `data/questions/compiler-construction.csv` (32 topics, 192 questions)
- `data/questions/operating-systems.csv` (37 topics, 222 questions)
- `data/questions/machine-learning.csv` (48 topics, 288 questions)
- `data/questions/web-engineering.csv` (48 topics, 288 questions)

### Quota & Quality Rules

Every topic requires exactly **6 questions**:
1. **3 Multiple Choice Questions (`mcq`)**:
   - Exactly 4 non-empty options (`option_a`, `option_b`, `option_c`, `option_d`).
   - Exactly one unambiguously correct answer letter (`A`, `B`, `C`, or `D`).
   - Plausible distractors (never use "all of the above" or "none of the above").
   - Balanced letter distribution across the subject (avoiding over-concentration in option A).
2. **1 True/False Question (`tf`)**:
   - `option_a` is "True" and `option_b` is "False".
   - `correct_answer` is strictly `"True"` or `"False"`.
   - Statements must evaluate non-trivial factual claims grounded in the topic's lecture note.
3. **1 Short Answer Question (`short`)**:
   - Concise target answers: 1 to 3 words per variant.
   - Accepted variants and synonyms separated by vertical bars `|` (e.g. `backtick|backticks|```).
4. **1 Theory Question (`theory`)**:
   - High-quality model answer of 2 to 4 complete sentences explaining principles, mechanisms, or trade-offs.
   - Reuses or expands upon the topic's note "Quick check" questions.
5. **Metadata**:
   - `semester`, `subject`, and `topic` must match `data/topics.csv` verbatim.
   - `source` must be set to `"generated"` on every row.

### How Teammates Validate Questions

Before committing any question additions or modifications, run the validation tool to verify schema, quotas, and constraints:

```bash
python scripts/validate_questions.py
```

The validation suite checks:
- The four original Semester 5 courses retain their 165 existing topics, each with exact question quotas (3 mcq, 1 tf, 1 short, 1 theory).
- No duplicate question texts within a topic.
- Non-empty options and valid answer keys.
- Balanced MCQ answer distribution per subject.
- Automated CI integration: `pytest tests/test_questions_validation.py` enforces these rules automatically.

### How Teammates Ingest Questions into the Database

Ingest questions into the local database using the Flask CLI. Always run with `--dry-run` first to validate integrity:

```bash
# 1. Validate via dry-run (no database changes persisted)
flask --app run.py load-questions --file data/questions/compiler-construction.csv --dry-run
flask --app run.py load-questions --file data/questions/operating-systems.csv --dry-run
flask --app run.py load-questions --file data/questions/machine-learning.csv --dry-run
flask --app run.py load-questions --file data/questions/web-engineering.csv --dry-run

# 2. Persist questions into database
flask --app run.py load-questions --file data/questions/compiler-construction.csv
flask --app run.py load-questions --file data/questions/operating-systems.csv
flask --app run.py load-questions --file data/questions/machine-learning.csv
flask --app run.py load-questions --file data/questions/web-engineering.csv
```

The loader is completely idempotent: running it against already-ingested files will report `0 Inserted, 0 Updated, N Unchanged` without duplicating records.

---

## Topic-Level Mastery Classification

The topic mastery Decision Tree uses **all attempts** by one user on one topic. Its five features are average score ratio, latest score ratio, best score ratio, attempt count, and trend (latest minus average). With no attempts, a topic has no mastery label. The dashboard, recommendations, prerequisite gap analysis, topic page, and quiz result use this aggregate label; the History page continues to show each attempt's individual label.

The synthetic training labels use a weighted score (40% average, 35% latest, 25% best), a 0.05 bonus for a positive trend or penalty for a negative trend, and small Gaussian noise. Scores below 0.50 map to Weak, below 0.70 to Good, below 0.90 to Better, and the rest to Excellent. The topic model is a Decision Tree with `criterion="entropy"` and `max_depth=5`; the training command reports holdout accuracy and the confusion matrix in `ml/reports/topic_label_model_metrics.json`.

The existing per-attempt model remains in place for History labels and is not post-adjusted by a separate improvement rule.

```bash
# Train the aggregate topic model and write its model, metrics, and tree artifacts:
flask --app run.py train-label-model

# Idempotently fill missing per-attempt History labels:
flask --app run.py label-attempts
```

---

## Prerequisite Knowledge Gap Analysis (Phase 6)

When a student struggles on a quiz and receives a **Weak** mastery assessment, StudySphere does not simply recommend retaking the same quiz blindly. Instead, it diagnoses foundational concept deficits by performing **Prerequisite Knowledge Gap Analysis**.

### Graph Traversal, Not Machine Learning (Viva Discussion Point)
> [!NOTE]
> **Viva Concept Clarity**: While topic mastery classification in Phase 5 is driven by a supervised Machine Learning Decision Tree model, **Prerequisite Gap Analysis is pure deterministic graph traversal (Breadth-First Search)** over the curriculum prerequisite directed graph. It involves zero machine learning inference, zero neural weights, and no probabilistic guessing. It is an algorithmic, explainable graph traversal algorithm operating directly on syllabus concept dependencies.

### Key Rules & Architecture

1. **The Gap Rule**:
   - A prerequisite topic is flagged as a **"gap"** if:
     - The student has **never attempted** that prerequisite topic (no attempt history), OR
     - The student's **aggregate topic mastery** on that prerequisite is **Weak**.
   - Prerequisites with aggregate mastery **Good**, **Better**, or **Excellent** are **not gaps** (they are already understood).
   - **Crucial Traversal Behavior**: Even when a prerequisite is mastered (`Good`/`Better`/`Excellent`), the graph walk **does not stop** at that node. It continues traversing through that node to inspect any deeper, transitive prerequisites that might still be unattempted or weak.

2. **The Depth Limit (Max Depth 4)**:
   - The BFS traversal is bounded to a maximum depth of **4 levels** backward from the target topic.
   - Bounding the depth prevents cognitive overload, ensuring the remediation roadmap focuses on immediately relevant foundational knowledge rather than pulling in the entire university curriculum back to primary school arithmetic.

3. **Ordering Rule (Deepest & Most Basic Topics First)**:
   - Gaps are returned ordered so the student revises the **most foundational concepts first**:
     1. **Depth Descending** (`-depth`): Deeper prerequisites (e.g., Depth 3 or 2) appear before the shallower topics that depend directly on them (e.g., Depth 1).
     2. **Ties Broken by Difficulty** (`Topic.difficulty` ascending): At the same depth, easier/more basic topics (e.g., Difficulty 1) appear before more challenging ones (e.g., Difficulty 3).
     3. **Ties Broken by Week** (`Topic.week` ascending): At the same depth and difficulty, topics introduced earlier in the semester syllabus appear first.
   - The resulting list is capped at **10 items** to keep the revision roadmap actionable.

4. **Cycle Safety**:
   - While an ideal academic curriculum forms a Directed Acyclic Graph (DAG), real-world curriculum definitions, manual edits, or student-uploaded modules might inadvertently introduce circular dependencies (e.g., Topic A $\rightarrow$ Topic B $\rightarrow$ Topic A).
   - The traversal maintains an explicit in-memory `visited` set. If an edge loops back to an already-evaluated topic, the traversal skips re-enqueuing that node, guaranteeing termination in $O(V + E)$ time and completely preventing infinite loops or recursion limits.

5. **Strict Query Budget (Constant $O(1)$ Queries)**:
   - To achieve sub-10ms response times and prevent $N+1$ database performance degradation, the service executes at most **3 SQL queries** (or **4 queries** total including target topic validation in web routes):
     - **Query 1**: Load all `Prerequisite` edges in a single query to construct the in-memory adjacency list.
     - **Query 2**: Load all of the student's attempts across visited topic IDs in one query, then calculate aggregate topic labels in memory/model inference.
     - **Query 3**: Fetch topic metadata and related courses for all identified gap topic IDs in a single query using `joinedload(Topic.course)` and `defer(Topic.content)`.
   - The query count remains strictly constant regardless of whether the curriculum graph contains 5 topics or 5,000 topics.

6. **Student Data Isolation**:
   - Gaps are calculated strictly and exclusively from the authenticated user's own attempt records (`Attempt.user_id == current_user.id`). One student's mastery or weakness has zero effect on another student's gap recommendations.

---

## Upload and LLM (Phase 7)

### Viva Preparation & Pipeline Architecture
> [!IMPORTANT]
> **Viva Concept Clarity**: Large Language Model (LLM) text summarization, explanation synthesis, and document image OCR/transcription are performed using Google's pre-trained Gemini foundation model accessed via the official Google Generative Language REST API (`gemini-3.5-flash-lite` or configurable). **We did not train or fine-tune this foundation model from scratch.**
> What we designed and implemented is the complete engineering pipeline, including:
> 1. Multi-modal ingestion for raw text, binary slide/whiteboard images, and educational web pages.
> 2. Zero-trust defense against Server-Side Request Forgery (SSRF), multi-hop redirect manipulation, and payload bloat.
> 3. True binary image signature verification and chunk validation without heavy local OCR runtime dependencies.
> 4. Prompt injection boundary isolation and strict instructional encapsulation.
> 5. Deterministic JSON schema enforcement, automatic schema repair, and single-hop retry fallback.
> 6. Dual-client architecture featuring `GeminiClient` with rate-limiting backoff and `FakeLLMClient` for offline deterministic testing.
> 7. Assessment quiz generation and answer evaluation engine with tolerant short-answer normalization.

### Security Architecture & Hardening Measures

1. **Server-Side Request Forgery (SSRF) Defense**:
   - URL inputs are strictly restricted to `http` and `https` schemes (schemes like `ftp://`, `file:///`, `gopher://`, or `javascript:` are rejected upfront).
   - Proactive DNS pre-flight verification resolves target hostnames to concrete IP addresses prior to initiating any HTTP connection.
   - All addresses in private, loopback, link-local, carrier-grade NAT, and reserved subnets are strictly blocked:
     - Loopback (`127.0.0.0/8`, `::1`)
     - RFC 1918 Private networks (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `fc00::/7`)
     - Link-local and cloud metadata services (`169.254.0.0/16`, `fe80::/10`)
     - Carrier-Grade NAT (`100.64.0.0/10`)
     - Broadcast, multicast, unspecified (`0.0.0.0`, `224.0.0.0/4`, `255.255.255.255`)
     - IPv4-mapped IPv6 aliases (`::ffff:127.0.0.1`, `::ffff:192.168.x.x`)
   - **Multi-Hop Redirect Re-Inspection**: Automatic redirects are disabled. For any redirect response (`301`, `302`, `303`, `307`, `308`), the destination URL is re-resolved through DNS and evaluated against the blocked subnet list before each subsequent request hop (capped at 3 maximum redirects).

2. **Strict Size Limits & Streaming Controls**:
   - **Pasted Text**: Enforces character boundary checks between 20 and 20,000 characters (`UPLOAD_MAX_TEXT_CHARS`).
   - **Uploaded Images**: Maximum binary size capped at 4 MB (`UPLOAD_MAX_IMAGE_MB`). Images are processed in-memory and never stored on disk or persistent database storage; only extracted text is retained.
   - **URL Fetching**: Streamed in 8 KB chunks with early termination if total content exceeds 2,000,000 bytes (2 MB, `URL_MAX_BYTES`).
   - **Network Timeout**: URL fetches enforce a strict 10-second socket timeout (`URL_FETCH_TIMEOUT`).
   - **Content-Type Restriction**: Validates `Content-Type` header; non-HTML/non-plain-text responses (e.g. PDFs, binary executables, audio, video) are rejected before reading data.

3. **Binary Image Signature & Structural Verification**:
   - Validates file signatures via real magic bytes rather than trusting client-provided file extensions:
     - **PNG**: 8-byte magic header (`\x89PNG\r\n\x1a\n`) followed by verified `IHDR` chunk length, type string, and CRC check. Fake PNG headers with random or truncated payloads are rejected.
     - **JPEG**: `\xff\xd8\xff` SOI markers followed by recognized segment markers (`JFIF`, `Exif`, `DQT`, `SOF0`).
     - **WEBP**: `RIFF` container header, `WEBP` fourCC, and recognized `VP8 ` / `VP8L` / `VP8X` format chunk.

4. **Prompt Injection Defense**:
   - Untrusted user study content is encapsulated within unambiguous delimiters:
     `<<<STUDY_MATERIAL_START>>>` and `<<<STUDY_MATERIAL_END>>>`.
   - The LLM prompt explicitly commands the foundation model to treat content inside delimiters strictly as passive study material to summarize, and to disregard any embedded instructions, commands, system role changes, or jailbreak overrides.

5. **Strict JSON Schema Validation & Automated Repair**:
   - LLM responses are parsed and validated against a strict schema:
     - `title`: String capped at 200 characters.
     - `summary`: Array containing between 5 and 8 concise bullet points (each capped at 500 characters).
     - `simple_explanation`: Plain-language explanation with short paragraphs and exactly one real-world analogy (capped at 3,000 characters).
     - `key_terms`: Between 1 and 10 items, each with `term` (<= 100 chars) and `meaning` (<= 300 chars).
     - `questions`: Exactly 6 questions (3 MCQ with 4 options each, 1 True/False, 1 Short Answer, and 1 Theory question with a model reference answer).
   - If an output is malformed or violates counts, an automated single-attempt retry request with error feedback is sent to the LLM.

6. **Defense-in-Depth HTML Sanitization**:
   - Every string returned from the LLM is sanitized with `nh3.clean` and `html.escape` to neutralize any potential stored Cross-Site Scripting (XSS) vectors.

7. **Per-User Quotas & Content Deduplication**:
   - Students are limited to 10 upload generations per 24 hours (`UPLOAD_DAILY_LIMIT=10`), with clear feedback upon reaching the limit.
   - Cleaned text content is hashed using SHA-256 (`content_hash`). Identical content uploaded by the same student immediately retrieves and reuses the existing `Upload` record without invoking the external LLM or consuming daily quota.

8. **Credential Security**:
   - `GEMINI_API_KEY` is loaded strictly from environment variables (`.env`).
   - The key is never rendered into templates, never stored in client JavaScript, and is scrubbed via sanitization filters from all error messages, outgoing URL logs, and exception tracebacks (`[REDACTED_API_KEY]`).

---

## Configuration Reference (Phase 7)

The following parameters govern Phase 7 ingestion and generation:

| Environment Variable | Default | Purpose & Constraints |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | *(None)* | Google Gemini API key from Google AI Studio. Stored in `.env` only. |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Configurable model identifier. Free-tier compatible models include `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`. |
| `GEMINI_TIMEOUT` | `120` | HTTP request timeout in seconds (120s read timeout, 10s connect timeout). |
| `LLM_PROVIDER` | `gemini` | `gemini` for live API synthesis; `fake` for deterministic offline testing. |
| `UPLOAD_MAX_TEXT_CHARS` | `20000` | Maximum character limit for pasted study material notes. |
| `UPLOAD_MAX_IMAGE_MB` | `4` | Maximum file size in MB for uploaded slide or whiteboard images. |
| `URL_FETCH_TIMEOUT` | `10` | Maximum socket timeout in seconds for fetching external URLs. |
| `URL_MAX_BYTES` | `2000000` | Maximum byte count (2 MB) downloaded during URL article extraction. |
| `UPLOAD_DAILY_LIMIT` | `10` | Daily generation quota per user to regulate external API usage. |

### Choosing a Current Free-Tier Model
Google AI Studio offers a free tier for developers with rate limits (RPM and TPM) that require no credit card billing:
1. `gemini-3.5-flash-lite`: Recommended default. High-speed multimodal processing with strong structured output adherence and low latency.
2. `gemini-3.1-flash-lite`: Alternative lightweight model for fast generation.

Configure your desired model in `.env`:
```bash
GEMINI_MODEL=gemini-3.5-flash-lite
```

---

## Database Migration & Supabase Production Deployment

Phase 7 introduces the `Upload` table and user custom instruction field managed under Flask-Migrate:
- **Migration Files**:
  - `migrations/versions/c7f91a2b3d4e_create_uploads_table.py` (`b4f8a1e2c9d0` &rarr; `c7f91a2b3d4e`)
  - `migrations/versions/d8a1b2c3e4f5_add_user_request_to_uploads.py` (`c7f91a2b3d4e` &rarr; `d8a1b2c3e4f5`)
- **Schema Features**: Includes foreign key to `users.id` with `ON DELETE CASCADE`, indexed `content_hash` for $O(1)$ duplicate lookups, JSON columns for structured summaries, key terms, and question banks, nullable `user_request` column for custom learning instructions, and PostgreSQL Row Level Security (RLS) enforcement.

> [!IMPORTANT]
> **Supabase Deployment Note**:
> While verified and applied locally on SQLite via environment overrides, revisions `c7f91a2b3d4e` and `d8a1b2c3e4f5` must be applied to the production Supabase PostgreSQL instance during production deployment:
> ```bash
> flask --app run.py db upgrade
> ```

---

## Decoupled Assessment Flow (Upload Quizzes)

Quizzes generated from uploaded study material use the platform's core evaluation engine (`evaluate_single_answer`, case-insensitive trimmed matching, and tolerant short-answer normalization ignoring leading English articles).

> [!NOTE]
> **Pedagogical Separation**:
> Upload quizzes **do NOT create `Attempt` table records** and do **NOT receive Decision Tree mastery labels**.
> This design decision ensures that ad-hoc, student-provided study materials do not contaminate formal curriculum mastery analytics, cohort feature vectors, or prerequisite knowledge gap graphs, which rely strictly on vetted, syllabus-aligned topic assessments.

---

## Design Decisions

- **Pre-trained API Model**: Utilized Google Gemini REST API directly with the Python `requests` library rather than bundling heavy third-party SDKs or local OCR binaries (e.g. Tesseract), keeping deployment containers lightweight.
- **Strict HTML Tag Elimination**: Applied `nh3.clean` and `html.escape` across all LLM-returned fields to completely eliminate Cross-Site Scripting (XSS) risks before database persistence and UI rendering.
- **True Image Binary Signature Verification**: Implemented PNG chunk and IHDR CRC checks, JPEG SOI segment validations, and WEBP RIFF chunk parsing to reject fake file headers before any network traffic is initiated.
- **Dynamic Multi-Hop SSRF Defense**: Disabled automatic redirect following in favor of per-hop DNS resolution to prevent attackers from bypassing SSRF filters via external 302 redirects to internal microservices.
- **Navbar Navigation Integration**: Added a direct "My material" navigation link in the top bar for authenticated users pointing to `/upload/` with reciprocal links between material creation and upload history.
- **Decoupled Assessment Persistence**: Tracked assessment performance metrics (`attempts_count`, `last_score`, `last_total`) directly on the `Upload` record rather than creating curriculum `Attempt` records, preserving the mathematical integrity of the Decision Tree classification model.
- **Parallel Sub-Request Generation**: Partitioned generation into two concurrent asynchronous tasks via `ThreadPoolExecutor(max_workers=2)` for study guide synthesis and quiz generation, reducing latency while preserving transactional consistency and daily quota accounting.
- **Optimized Timeout and Retry Policy**: Configured `GEMINI_TIMEOUT` to 120s read timeout and 10s connect timeout without read-timeout retries, reserving single-attempt backoff retries for 429 rate limits, 5xx gateway faults, and unsupported `generationConfig` fields.
- **Cross-Part Monolithic Payload Fallback**: Maintained backward compatibility with monolithic test mocks by extracting guide and quiz artifacts from unified responses when available.
- **URL SSRF Hostname vs. IP Literal Separation**: Resolved the GeeksForGeeks false-positive by separating IP literal parsing from DNS hostname resolution in `resolve_and_verify_host` and ensuring `is_ip_blocked` does not treat non-IP hostnames as blocked IPs.
- **SSRF Connected Peer Verification vs. Raw IP Trade-off**: Re-verified the connected socket's peer IP address via `sock.getpeername()` after connection rather than rewriting URLs directly to raw IPs, preventing DNS rebinding attacks while preserving TLS Server Name Indication (SNI) and HTTP virtual hosting compatibility for CDNs like AWS CloudFront and Cloudflare.
- **Friendly URL Extraction Failure Diagnostics**: Mapped HTTP 401/403 responses to clear user guidance suggesting direct copy-pasting for anti-bot protected sites, while distinguishing private/blocked IP violations, size limits, timeouts, and non-HTML content types.
- **User Instruction Prompt Isolation**: Sandboxed the optional "What do you want to do with this material?" instruction inside `<<<USER_REQUEST_START>>> ... <<<USER_REQUEST_END>>>` blocks in both study guide and quiz prompts with strict system instructions prohibiting role or schema overrides, and sanitizing output via HTML escaping.
- **Instruction-Aware Content Deduplication**: Extended `compute_upload_content_hash` to include the normalized user instruction as `sha256(text + "|||" + user_request)` while falling back to `sha256(text)` for empty instructions, preserving duplicate reuse for legacy uploads while generating fresh artifacts when instructions differ.
- **Nullable User Request Column & Supabase Migration**: Added nullable `user_request` text column to `Upload` via batch migration `d8a1b2c3e4f5_add_user_request_to_uploads.py`, applied locally to SQLite, which must be executed on Supabase PostgreSQL in production via `flask --app run.py db upgrade`.
- **Rule-Based Adaptive Tier Hierarchy**: Orchestrated adaptive recommendations and related topic reranking through a 5-tier pedagogical priority rule engine (Tier 1: Prerequisite gaps of Weak topics deepest first; Tier 2: Weak topics to retake; Tier 3: Unattempted topics ready to learn; Tier 4: Good/Better practice; Tier 5: Excellent mastered) with TF-IDF similarity tie-breaking, bound to O(1) query budgets (<= 5 queries) and locally vendored Chart.js to eliminate external CDN dependencies.
- **Multi-Theme Tokenization & Provenance Consolidation**: Implemented CSS custom property tokenization for Light, Dark, and High-Contrast Highlight themes on html[data-theme] with synchronous pre-paint state execution to prevent theme flash, dynamic Chart.js theme listeners, and consolidated unreviewed AI provenance to a single dedicated banner on topic notes.

---

## Adaptive Recommendations and Dashboard (Phase 8)

### Pedagogical Tier Priority Rules

StudySphere synthesizes student assessment history and curriculum graph structure to generate personalized study recommendations through a 5-tier pedagogical priority hierarchy:

1. **Tier 1: Prerequisite Gaps of Weak Topics (Deepest First)**
   - When a student's aggregate topic mastery is **Weak**, the system does not merely tell them to repeat the same quiz. Instead, it recursively traverses backwards through the curriculum prerequisite DAG (using breadth-first search up to depth 4).
   - Any foundational prerequisite the student has never attempted or has **Weak aggregate topic mastery** on is identified as a critical gap.
   - These prerequisite gaps are placed at the absolute top of the study queue, ordered **deepest first** (highest DAG depth), ensuring the student repairs foundational root causes before advancing.
   - Rationale: *"Prerequisite of [Weak Topic Name], which has Weak topic mastery"*.

2. **Tier 2: The Weak Topics Themselves (Retake)**
   - After addressing the prerequisite gaps, the student must revisit the topic they struggled with to verify remediation and rebuild mastery.
   - Rationale: *"Topic mastery is Weak — retake to build mastery"*.

3. **Tier 3: Ready to Learn (Unattempted Topics)**
   - Topics in the student's enrolled academic semester that have **not yet been attempted**, but whose prerequisites have **all been satisfied** (attempted and scored Good, Better, or Excellent, or having no prior prerequisites).
   - Ordered chronologically by course, academic week, and difficulty rating.
   - Rationale: *"Ready to learn — all prerequisites met"*.

4. **Tier 4: Practice to Solidify (Good & Better)**
   - Topics where the student demonstrated solid or strong understanding, but has not yet reached full mastery (score < 90% or labeled Good / Better).
   - Provides targeted reinforcement to elevate proficiency into full mastery.
   - Rationale: *"Scored [Good / Better] — practice to reach mastery"*.

5. **Tier 5: Mastered Topics Last (Excellent)**
   - Topics where the student demonstrated outstanding mastery (**Excellent** label).
   - These are kept at the end of recommendations as periodic refreshers and are never forcibly discarded.
   - Rationale: *"Mastered (Excellent) — review or refresh"*.

---

### Why Rule-Based on Top of Decision Tree and TF-IDF?

A key question in academic vivas is: *Why use a rule-based ranking system rather than training an end-to-end black-box machine learning model for recommendations?*

1. **Separation of Concerns & Specialized ML Models**:
   - **Machine Learning is used where it excels**:
     - **TF-IDF + Cosine Similarity** computes semantic content closeness across unstructured lecture notes and syllabus vocabularies.
     - **Decision Tree Classifier** maps non-linear quiz performance features (`score_ratio`, `wrong_ratio`, `total_questions`, `attempt_number`, `previous_score_ratio`, `improvement`) into discrete pedagogical mastery tiers (**Weak**, **Good**, **Better**, **Excellent**).
   - **Curriculum Constraints Require Deterministic Guarantees**:
     - Academic curricula have strict pedagogical preconditions: a student *cannot* learn backpropagation if they do not understand the chain rule or dot products.
     - Pure collaborative filtering or deep reinforcement learning can suggest topics out-of-order (e.g., suggesting advanced transformers before matrix multiplication simply because other students clicked it).
     - Rule-based sequencing over the DAG guarantees pedagogical correctness, curriculum adherence, and zero hallucinations.

2. **Full Explainability & Student Agency**:
   - Every recommendation comes with an explicit, plain-English reason (e.g., *"Prerequisite of Perceptron, which has Weak topic mastery"*).
   - Students understand *why* a topic is recommended, building trust and educational clarity.

3. **Sub-50ms Predictability & Low Latency**:
   - Rule-based tier evaluation over an in-memory adjacency list executes in < 5 ms, requiring zero GPU overhead, zero model drift monitoring, and fixed $O(1)$ query counts ($\le 5$ database queries per request).

---

### How the Three Core Parts Work Together

StudySphere's adaptive intelligence functions as a cohesive tripartite pipeline:

```mermaid
flowchart LR
    A["Quiz Attempt"] --> B["1. Decision Tree Classifier<br/>(Mastery: Weak / Good / Better / Excellent)"]
    B -->|If Weak| C["2. Knowledge Gap Analysis<br/>(BFS DAG Traversal & Deepest Prereq Gaps)"]
    B -->|If Good / Better / Excellent| D["3. Adaptive Recommendation Engine<br/>(5 Pedagogical Tiers)"]
    C --> D
    E["TF-IDF Recommender<br/>(Lecture Notes Content Similarity)"] -->|Similarity Tie-Breaker| D
    D --> F["Interactive Dashboard &<br/>Reranked Related Topics Sidebar"]
```

1. **The Recommender (`ml/recommender.py`)**:
   - Analyzes topic titles, descriptions, metadata tags, and authoritative Markdown lecture notes using scikit-learn's `TfidfVectorizer`.
   - Computes pairwise cosine similarity matrices with an additive boost for shared academic subjects.
   - Serves as the content-similarity tie-breaker inside each pedagogical tier.

2. **The Decision Tree Classifier (`ml/label_model.py`)**:
   - Evaluates multidimensional performance vectors from student quiz attempts.
   - Categorizes performance into actionable mastery tiers: **Weak** (remediation required), **Good** (solid foundation), **Better** (strong grasp), or **Excellent** (mastered).
   - Acts as the catalyst that dynamically alters a student's standing on each curriculum node.

3. **The Knowledge Gap Analysis (`app/services/gap_analysis.py` & `app/services/adaptive_service.py`)**:
   - When the Decision Tree flags an attempt as **Weak**, graph traversal algorithms trace directed dependency edges backwards to isolate unmastered root causes.
   - Dynamically reorganizes the student's dashboard ("Revise First" and "Recommended Next") and re-ranks the topic page's "Related Topics" sidebar to direct student attention to foundational gaps before advancing.

## Design decisions

- The request specified three commits but only two implementation tasks and commit messages; the third commit records this scope gap rather than inventing product work.
- Resource links are curated only for Semester 5; the source CSV contains 171 Semester 5 topics, including six in Computer Architecture and Linear Algebra beyond the 165 named in the request.
- Homepage chat history groups saved messages by topic or upload, and deleting a conversation removes only the signed-in user's messages.
- The sidebar collapse preference persists across visits; mobile keeps its drawer closed by default regardless of the desktop rail preference.
- Hugging Face Spaces is treated as a single trusted reverse-proxy hop; production alone applies ProxyFix so forwarded HTTPS and host headers work with secure cookies, CSRF, and generated URLs.
- Image text extraction uses the configured multimodal LLM directly; EasyOCR and pytesseract are not imported or required, so local OCR dependencies cannot block application startup.
