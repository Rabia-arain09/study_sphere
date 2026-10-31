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
│   ├── topics.csv               # 165 syllabus topics with tags, difficulty & week
│   ├── topic_prerequisites.csv  # 194 directed topic-level concept prerequisites
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
├── run.py                   # Application entry point for development and WSGI
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

The `setup-local-db` command prepares the schema (applying migrations or `create_all`), ingests the entire curriculum dataset, and populates all study notes so your local database has the exact same **44 courses**, **165 topics**, and **165 notes** as Supabase. It is strictly idempotent and refuses to run against PostgreSQL databases.

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
      Processed 44 courses, 165 topics, 12 course prerequisites, 194 topic prerequisites.
[3/3] Ingesting study notes...
      Processed 165 note files (165 updated, 0 unchanged, 0 skipped).
============================================================
 Local SQLite database setup completed successfully!
> Total Courses : 44 (expected: 44)
> Total Topics  : 165 (expected: 165)
> Total Notes   : 165 (expected: 165)
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

### 5. Run the Application
```bash
python run.py
```
The server will start at `http://127.0.0.1:5000/`. You can verify health at `http://127.0.0.1:5000/health`.

### 6. Run Automated Tests
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
   - **Inverse Document Frequency (IDF)**: Measures how unique or informative a word is across all 165 curriculum topics ($\log \frac{N}{\text{df}} + 1$). Common words across all topics (like "system" or "introduction") receive low IDF weights, while specialized terms (like "perceptron", "deadlock", "syntax") receive high IDF weights.
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
- **Local SQLite Environment & Safe Migration Pipeline**: Built `setup-local-db` CLI command that validates SQLite dialect, runs migrations with `create_all` fallback, loads curriculum CSVs and Markdown notes idempotently (44 courses, 165 topics, 165 notes), and strictly refuses execution against PostgreSQL.
- **Instance-Relative Path Normalization**: Resolved relative `sqlite:///instance/` URIs in `create_app` against repository root to prevent Flask-SQLAlchemy 3.x from double-nesting paths into `instance/instance/studysphere.db`.
- **TF-IDF Topic Name Repetition Weighting**: Repeated topic name 3 times during document text aggregation in `ml/recommender.py` to give primary title keywords prominent feature weighting above secondary description and body text.
- **Sublinear Term Frequency Scaling**: Configured `sublinear_tf=True` in `TfidfVectorizer` to scale term frequencies logarithmically ($1 + \log(\text{tf})$), dampening the influence of repetitive keywords in detailed lecture notes.
- **Same-Subject Additive Score Boost**: Applied a +0.05 additive boost (capped at 1.0) to candidate topics sharing the same academic subject/course when base cosine similarity is positive, maintaining curriculum cohesion without suppressing genuine cross-course connections.
- **Lazy In-Memory Recommender Lifecycle**: Initialized `TopicRecommender` lazily on first access, cached the fitted instance in memory, and re-fitted automatically only when database state keys (topic count, max ID, or content length checksum) mutate.
- **Batched Single-Query Related Topic Retrieval**: Fetched target topic existence and all top-k recommendation entities in a single database query using `in_([topic_id] + rec_ids)` with eager-loaded `joinedload(Topic.course)`, avoiding N+1 queries and achieving ~4ms response latency.
- **Course Title Fallback for Related Topics**: In `GET /topics/<id>/related` and UI cards, resolved the `course` property from `topic.course.title` falling back to `topic.subject` to provide clear academic subject titles.
- **RESTful 404 on Missing Target in Related Endpoint**: Handled unknown topic IDs in `GET /topics/<id>/related` with HTTP 404 to match `/topics/<id>`, while returning an empty JSON array `[]` for valid topics with zero matching recommendations.
