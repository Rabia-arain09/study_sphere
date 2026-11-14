---
title: StudySphere
sdk: docker
app_port: 7860
---

# StudySphere 🎓

**An adaptive, ML-based personalized study platform.**
Students browse their curriculum, read notes, take quizzes, and get a mastery label for every topic. When a topic is weak, the app finds the prerequisite topics to revise first.

| | |
|---|---|
| **Team** | [Rabia arain , isha , awais memon] |
| **Supervisor** | [mam marina] |
| **Department** | [CS, sukkur iba] |
| **Courses** | Machine Learning, Web Engineering |

---

## 1. What the app does

1. **Browse** Semester → Subject → Topic and read clean, sanitized Markdown notes.
2. **Related topics** are recommended with TF-IDF and cosine similarity.
3. **Quiz** every topic (MCQ, True/False, short answer, theory with self-check).
4. A **Decision Tree** gives each topic a mastery label: *Weak, Good, Better, Excellent*.
5. **Gap analysis** lists the prerequisite topics to revise first when a topic is Weak.
6. **Upload** your own material (text, image, URL, PDF, PPTX, DOCX) and get a summary, a simple explanation, key terms and a quiz.
7. **Dashboard** shows progress charts, weak topics and a *Recommended next* list that changes after every quiz.
8. **Study chat** answers questions only from the topic notes or your uploaded material.

## 2. Machine learning in this project

| Component | Technique | Built by us? |
|---|---|---|
| Topic recommender | TF-IDF + cosine similarity (scikit-learn) | Yes |
| Mastery label | Decision Tree, entropy, `max_depth=5` | Yes |
| Knowledge-gap analysis | Breadth-first search on the prerequisite graph | Yes (algorithm, **not** ML) |
| Adaptive ranking | 5 pedagogical tier rules + similarity as tie-breaker | Yes (rule-based) |
| Summaries, quiz generation, image reading | Google Gemini (pre-trained model through an API) | No |

**Honest notes**
- The Decision Tree is trained on a **synthetic, rule-labelled dataset**, so its high accuracy shows that it learned the labelling rules. It can be retrained on real student attempts (`flask --app run.py train-label-model`).
- Metrics and the tree are saved in `ml/reports/`.
- All notes and questions are **AI-generated and marked "not reviewed"** until a teammate verifies them.

## 3. Content in the database

- **Semester 5 core subjects:** Machine Learning (48 topics), Operating Systems (37), Compiler Construction (32), Web Engineering (48), a total of 165 topics, each with a note and **6 questions** (990 questions).
- 44 degree courses and their prerequisite links are loaded from CSV files in `data/`.

## 4. Tech stack

| Layer | Tools |
|---|---|
| Backend | Python, Flask (application factory + blueprints), Flask-Login, Flask-WTF (CSRF) |
| Database | SQLAlchemy + Flask-Migrate; Supabase PostgreSQL in production, SQLite locally |
| ML | scikit-learn, pandas, NumPy, joblib |
| Frontend | Jinja2, HTML, CSS, JavaScript, Chart.js (bundled locally); Light / Dark / High-contrast themes |
| AI | Gemini REST API (key in `.env` only) |
| Quality | pytest test suite |

## 5. Project structure

```
app/            Flask app: blueprints (auth, topics, quiz, upload, dashboard), models, services, templates
ml/             Recommender, Decision Tree trainer, saved metrics (ml/reports)
data/           Curriculum CSVs, Markdown notes, question banks
migrations/     Database migrations
scripts/        Validation and helper scripts
tests/          Automated tests
```

## 6. Run it locally (Windows PowerShell)

```powershell
git clone https://github.com/Rabia-arain09/study_sphere.git
cd study_sphere
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env

$env:DATABASE_URL = "sqlite:///instance/studysphere.db"
flask --app run.py setup-local-db     # create tables, load courses, topics, notes
flask --app run.py load-questions --file data/questions/machine-learning.csv   # repeat for the other 3 files in data/questions/
flask --app run.py run
```

Open **http://127.0.0.1:5000**, sign up, and browse.

- If Windows blocks `flask.exe`, use `python -m flask --app run.py run`.
- `DATABASE_URL` only lasts for the current terminal window.
- For the AI features, add `GEMINI_API_KEY` to `.env`. Use `LLM_PROVIDER=fake` to work offline.
- Run the tests with `pytest`.

## 7. Deployment

The repo includes `render.yaml` (Render) and a `Dockerfile` (Hugging Face Spaces, port 7860).
Required settings: `SECRET_KEY`, `DATABASE_URL`, `GEMINI_API_KEY`, `LLM_PROVIDER`, `GEMINI_MODEL`.
After deploying, run `flask --app wsgi db upgrade`. Health check: `/health`.

## 8. Security

- Passwords are hashed, forms are CSRF-protected, and Markdown and AI output are sanitized.
- Uploads: size limits, real image-signature checks, and SSRF protection for URLs (private and local addresses are blocked, redirects are re-checked).
- Uploaded text is treated as untrusted (prompt-injection defence), with a daily limit per user.
- Secrets live only in `.env`, which is never committed.

## 9. Known limitations

- Only Semester 5 has full notes and quizzes.
- AI-written notes and questions still need teacher or teammate review.
- Quizzes made from uploads are not counted in mastery labels.
- The Gemini free tier can be slow; an upload may take up to 1–2 minutes.

## 10. More details

The full developer guide (data formats, CLI commands, migrations, design decisions, viva notes) is in [`docs/DEVELOPER_GUIDE.md`](docs/DEVELOPER_GUIDE.md).
