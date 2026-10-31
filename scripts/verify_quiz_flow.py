"""Verification script for StudySphere quiz engine workflow and response time performance."""

from __future__ import annotations
import os
import sys
import time
from pathlib import Path

# Ensure repository root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure Windows console handles UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Temporary env override for SQLite (do not modify .env)
sqlite_path = (BASE_DIR / "instance" / "studysphere_quiz_verify.db").resolve()
os.environ["DATABASE_URL"] = f"sqlite:///{sqlite_path.as_posix()}"

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.topic import Topic
from app.models.attempt import Attempt
from app.services.curriculum_loader import load_curriculum
from app.services.notes_loader import load_notes
from app.services.question_loader import load_questions


def run_verification() -> bool:
    """Run full quiz workflow on SQLite, measure timings, and cleanly delete temporary user."""
    print("=" * 70)
    print(" StudySphere Phase 4 Quiz Engine & Performance Verification (SQLite)")
    print("=" * 70)
    print(f"> Target Database : sqlite:///{sqlite_path.as_posix()}")

    app = create_app("development")
    temp_email = "temp_quiz_verifier@example.com"
    temp_pass = "VerifyQuizPass123!"

    with app.app_context():
        # 1. Prepare clean database schema
        db.create_all()

        # Ingest curriculum & questions if needed
        if Topic.query.count() == 0:
            print("[1/5] Ingesting curriculum & notes into temporary SQLite db...")
            load_curriculum(data_dir="data", dry_run=False)
            load_notes(notes_dir="data/notes", dry_run=False)
        else:
            print("[1/5] Curriculum already loaded.")

        print("[2/5] Ingesting sample questions from data/questions.csv...")
        q_summary = load_questions(file_path="data/questions.csv", dry_run=False)
        print(f"      Processed {q_summary.total_rows} questions (inserted: {q_summary.inserted}, unchanged: {q_summary.unchanged}).")

        # Find target topic with questions
        target_topic = Topic.query.filter_by(
            name="Introduction to Machine Learning", semester=5
        ).first()
        assert target_topic is not None, "Target topic 'Introduction to Machine Learning' not found!"
        topic_id = target_topic.id
        print(f"      Target Topic: '{target_topic.name}' (ID: {topic_id})")

        # 2. Clean up any leftover temporary user
        existing_user = User.query.filter_by(email=temp_email).first()
        if existing_user:
            db.session.delete(existing_user)
            db.session.commit()

        # 3. Create temporary test student
        print("[3/5] Creating temporary test student...")
        student = User(
            name="Temporary Quiz Verifier",
            email=temp_email,
            semester=5,
        )
        student.set_password(temp_pass)
        db.session.add(student)
        db.session.commit()
        student_id = student.id
        print(f"      Created student ID: {student_id}")

        all_under_one_second = True

        try:
            with app.test_client() as client:
                import re

                # Extract CSRF token from login form
                get_login = client.get("/auth/login")
                csrf_match = re.search(
                    r'name="csrf_token"\s+type="hidden"\s+value="([^"]+)"',
                    get_login.data.decode("utf-8", errors="replace"),
                ) or re.search(
                    r'value="([^"]+)"\s+name="csrf_token"',
                    get_login.data.decode("utf-8", errors="replace"),
                )
                assert csrf_match, "Failed to extract login CSRF token"
                login_csrf = csrf_match.group(1)

                # Authenticate
                login_resp = client.post(
                    "/auth/login",
                    data={
                        "csrf_token": login_csrf,
                        "email": temp_email,
                        "password": temp_pass,
                    },
                    follow_redirects=True,
                )
                assert login_resp.status_code == 200, "Authentication failed"

                print("\n[4/5] Testing pages and measuring response times...")
                print("-" * 70)
                print(f"{'Endpoint':<35} | {'Status':<6} | {'Time (ms)':>10} | {'Under 1s?':<9}")
                print("-" * 70)

                # Page 1: Topic detail page before attempts
                t0 = time.perf_counter()
                r_topic = client.get(f"/topics/{topic_id}")
                elapsed_topic = (time.perf_counter() - t0) * 1000
                under_1s = elapsed_topic < 1000.0
                all_under_one_second &= under_1s
                print(f"{'/topics/' + str(topic_id):<35} | {r_topic.status_code:<6} | {elapsed_topic:9.2f}ms | {'PASS' if under_1s else 'FAIL':<9}")
                assert r_topic.status_code == 200
                assert b"Take Quiz" in r_topic.data

                # Page 2: Quiz form
                t0 = time.perf_counter()
                r_quiz = client.get(f"/quiz/topic/{topic_id}")
                elapsed_quiz = (time.perf_counter() - t0) * 1000
                under_1s = elapsed_quiz < 1000.0
                all_under_one_second &= under_1s
                print(f"{'/quiz/topic/' + str(topic_id):<35} | {r_quiz.status_code:<6} | {elapsed_quiz:9.2f}ms | {'PASS' if under_1s else 'FAIL':<9}")
                assert r_quiz.status_code == 200

                # Extract CSRF token from quiz form
                quiz_csrf_match = re.search(
                    r'name="csrf_token"\s+value="([^"]+)"',
                    r_quiz.data.decode("utf-8", errors="replace"),
                ) or re.search(
                    r'value="([^"]+)"\s+name="csrf_token"',
                    r_quiz.data.decode("utf-8", errors="replace"),
                )
                quiz_csrf = quiz_csrf_match.group(1) if quiz_csrf_match else ""

                # Page 3: Submit quiz
                post_data: dict[str, str] = {"csrf_token": quiz_csrf}
                for q in target_topic.questions:
                    post_data[f"question_{q.id}"] = q.correct_answer

                t0 = time.perf_counter()
                r_submit = client.post(
                    f"/quiz/topic/{topic_id}/submit",
                    data=post_data,
                    follow_redirects=False,
                )
                elapsed_submit = (time.perf_counter() - t0) * 1000
                under_1s = elapsed_submit < 1000.0
                all_under_one_second &= under_1s
                print(f"{'/quiz/topic/' + str(topic_id) + '/submit':<35} | {r_submit.status_code:<6} | {elapsed_submit:9.2f}ms | {'PASS' if under_1s else 'FAIL':<9}")
                assert r_submit.status_code == 302
                redirect_url = r_submit.headers["Location"]
                attempt_id_str = redirect_url.split("/")[-1]
                attempt_id = int(attempt_id_str)

                # Page 4: Attempt result page
                t0 = time.perf_counter()
                r_result = client.get(f"/quiz/attempt/{attempt_id}")
                elapsed_result = (time.perf_counter() - t0) * 1000
                under_1s = elapsed_result < 1000.0
                all_under_one_second &= under_1s
                print(f"{'/quiz/attempt/' + str(attempt_id):<35} | {r_result.status_code:<6} | {elapsed_result:9.2f}ms | {'PASS' if under_1s else 'FAIL':<9}")
                assert r_result.status_code == 200
                assert b"Quiz Results" in r_result.data
                assert b"Detailed Question Review" in r_result.data

                # Page 5: Topic detail page after attempt (displaying last attempt and count)
                t0 = time.perf_counter()
                r_topic_after = client.get(f"/topics/{topic_id}")
                elapsed_topic_after = (time.perf_counter() - t0) * 1000
                under_1s = elapsed_topic_after < 1000.0
                all_under_one_second &= under_1s
                print(f"{'/topics/' + str(topic_id) + ' (with attempt)':<35} | {r_topic_after.status_code:<6} | {elapsed_topic_after:9.2f}ms | {'PASS' if under_1s else 'FAIL':<9}")
                assert r_topic_after.status_code == 200
                assert b"Total Attempts:" in r_topic_after.data
                assert b"Last Score:" in r_topic_after.data

                print("-" * 70)

        finally:
            # 5. Delete temporary student and attempts
            print("\n[5/5] Deleting temporary test student and cleaning up...")
            user_to_delete = db.session.get(User, student_id)
            if user_to_delete:
                db.session.delete(user_to_delete)
                db.session.commit()
                print("      Temporary user cleanly removed from SQLite database.")

            # Double check verification
            verified_deleted = db.session.get(User, student_id)
            assert verified_deleted is None, "Failed to delete temporary user!"

    print("\n" + "=" * 70)
    if all_under_one_second:
        print(" ALL VERIFICATION CHECKS PASSED: Every page responded in < 1 second!")
    else:
        print(" VERIFICATION WARNING: One or more pages took >= 1 second.")
    print("=" * 70)

    # Clean up temporary SQLite db file
    try:
        if sqlite_path.exists():
            sqlite_path.unlink()
    except Exception:
        pass

    return all_under_one_second


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
