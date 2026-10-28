# StudySphere 🎓

StudySphere is a production-grade, adaptive ML-based personalized study platform. Students navigate through their curriculum hierarchically (**Semester &rarr; Subject &rarr; Topic**), complete topic-specific quizzes, and receive automated mastery assessments powered by a **scikit-learn Decision Tree classifier** that categorizes topic mastery into **Strong**, **Needs Revision**, or **Weak**.

When foundational deficits are detected, StudySphere performs **prerequisite-based knowledge gap analysis** across curriculum concept dependency graphs. Additionally, students can upload unstructured study materials (raw text, document images, or web URLs) to extract concepts via OCR and automatically synthesize summaries and calibrated questions via LLM pipelines.

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
    end

    subgraph Services["Service & Domain Logic (app/services/)"]
        GapAnalysis["Knowledge Gap Graph Traversal (DAG)"]
        QuizEngine["Scoring & Evaluation Engine"]
        IngestionService["OCR & LLM Synthesis Pipeline"]
    end

    subgraph ML["Machine Learning Pipeline (ml/)"]
        DTClassifier["Decision Tree Mastery Classifier"]
        FeatureExtractor["Feature Vector Preprocessor"]
        ModelStorage["Joblib Model Artifacts"]
    end

    subgraph DB["Persistence Layer (SQLAlchemy ORM)"]
        UsersTbl[("users")]
        TopicsTbl[("topics")]
        PrereqsTbl[("prerequisites")]
        ResourcesTbl[("resources")]
        QuestionsTbl[("questions")]
        AttemptsTbl[("attempts")]
    end

    UI --> AuthBP & TopicsBP & QuizBP & UploadBP & DashBP
    AuthBP & TopicsBP & QuizBP & UploadBP & DashBP --> Factory
    Factory --> Extensions & Config
    QuizBP --> QuizEngine
    UploadBP --> IngestionService
    DashBP --> GapAnalysis
    QuizEngine --> FeatureExtractor --> DTClassifier
    DTClassifier --> ModelStorage
    GapAnalysis --> PrereqsTbl
    Extensions --> DB
    Services --> DB
```

---

## Folder Structure

```text
study_sphere/
├── app/
│   ├── __init__.py          # create_app application factory & route registration
│   ├── config.py            # Development, Testing, Production configurations & DB fallback
│   ├── extensions.py        # SQLAlchemy & Flask-Migrate extension singletons
│   ├── blueprints/          # Modular domain-driven route handlers
│   │   ├── __init__.py      # Blueprint package exporter
│   │   ├── auth/            # Authentication, session, and student registration
│   │   ├── topics/          # Semester > Subject > Topic browsing & syllabus tree
│   │   ├── quiz/            # Quiz sessions, answer evaluation, and attempt recording
│   │   ├── upload/          # Multimodal ingestion (OCR text/image/URL)
│   │   └── dashboard/       # Knowledge gap visualization & mastery analytics
│   ├── models/              # Relational models with ML pipeline docstrings
│   │   ├── __init__.py      # Model registry exporter
│   │   ├── user.py          # User authentication and cohort profile
│   │   ├── topic.py         # Curriculum nodes with difficulty check & composite uniqueness
│   │   ├── prerequisite.py  # Directed knowledge graph edges & self-reference checks
│   │   ├── resource.py      # Targeted remediation media (notes, diagrams, links)
│   │   ├── question.py      # Assessment bank items (curriculum & OCR/LLM generated)
│   │   └── attempt.py       # Attempt logs, feature inputs & Decision Tree mastery labels
│   ├── services/            # Domain logic (knowledge gap traversal, OCR/LLM integration)
│   │   └── __init__.py
│   ├── static/              # Frontend static assets
│   │   ├── css/main.css
│   │   ├── js/main.js
│   │   └── img/
│   └── templates/           # Jinja2 presentation templates
│       └── base.html
├── data/                    # Dataset benchmarks, training datasets, and exports
├── migrations/              # Alembic / Flask-Migrate migration scripts
│   ├── versions/            # Versioned migration revision files
│   └── env.py
├── ml/                      # Scikit-learn pipelines, Decision Tree trainer & inference
│   └── __init__.py
├── tests/                   # Pytest automated test suite
│   ├── __init__.py
│   ├── conftest.py          # App and test fixtures
│   ├── test_factory.py      # App factory and health checks
│   └── test_models.py       # Model constraints, foreign keys, and relationships
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
  DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@db.YOUR_SUPABASE_HOST.supabase.co:5432/postgres
  ```
- Configure `SECRET_KEY` and optional `LLM_API_KEY`.

### 5. Apply Database Migrations
Generate tables using Flask-Migrate:
```bash
flask --app run.py db upgrade
```

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

## Design Decisions

- **Application Factory Pattern**: Adopted `create_app()` factory with modular Blueprint separation (`auth`, `topics`, `quiz`, `upload`, `dashboard`) to isolate developer workflows and eliminate circular dependencies.
- **Dynamic Database Adapter Switching**: Configured `app/config.py` to automatically normalize Supabase `postgres://` or `postgresql://` URIs to `postgresql+psycopg2://` while falling back to zero-config SQLite (`instance/studysphere.db`).
- **Standardized Migration Naming Conventions**: Enforced explicit SQLAlchemy `MetaData` constraint naming convention (`ix_`, `uq_`, `ck_`, `fk_`, `pk_`) in `app/extensions.py` to prevent unnamed constraint errors during SQLite and PostgreSQL migrations.
- **Portability of Enumerations**: Implemented `native_enum=False` on `ResourceType`, `QuestionType`, `QuestionSource`, and `MasteryLabel` to maintain identical schema definitions and validation between local SQLite development and Supabase PostgreSQL production.
- **Explicit Prerequisite Association Entity**: Modeled topic prerequisites via a dedicated `Prerequisite` model with `CASCADE` deletions and a `CHECK(topic_id != prerequisite_topic_id)` constraint to enable recursive DAG traversals during knowledge gap analysis.
- **Flexible JSON Payload Storage**: Stored quiz question options (`Question.options`) and topic tags (`Topic.tags`) using standard SQLAlchemy `JSON` types to support polymorphic question structures (MCQ options vs theoretical rubrics) without requiring fragile schema alterations.
- **Decoupled ML Lifecycles**: Isolated scikit-learn models and feature processing under `ml/` and `app/services/` so machine learning training artifacts remain decoupled from web request-response threads.