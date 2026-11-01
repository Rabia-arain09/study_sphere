"""Verification script for StudySphere quiz workflow on SQLite.

Tests one topic per Semester 5 subject:
- Compiler Construction
- Operating Systems
- Machine Learning
- Web Engineering

Measures latency (< 1.0 second per page load) for GET /quiz/topic/<id>,
POST /quiz/topic/<id>/submit, and GET /quiz/attempt/<id>.
Creates a temporary user, executes the quiz attempts, and deletes the temporary user and attempts cleanly.
Never prints any secrets.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Ensure SQLite instance database is targeted
os.environ["DATABASE_URL"] = "sqlite:///instance/studysphere.db"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.topic import Topic
from app.models.course import Course
from app.models.attempt import Attempt
from app.models.question import Question


def verify_quiz_flow() -> None:
    app = create_app()
    app.config["TESTING"] = False
    app.config["WTF_CSRF_ENABLED"] = False  # Simplify test client form submission

    client = app.test_client()

    with app.app_context():
        # 1. Create temporary test user
        temp_email = f"temp_verifier_{int(time.time())}@example.com"
        temp_user = User(
            name="Temporary Quiz Verifier",
            email=temp_email,
            semester=5,
        )
        temp_user.set_password("TempPassword123!")
        db.session.add(temp_user)
        db.session.commit()
        user_id = temp_user.id
        print(f"> Created temporary test user with ID: {user_id}")

        try:
            # 2. Log in temporary user via test client
            login_resp = client.post(
                "/auth/login",
                data={"email": temp_email, "password": "TempPassword123!"},
                follow_redirects=True,
            )
            assert login_resp.status_code == 200, f"Login failed: status {login_resp.status_code}"
            print("> Authenticated temporary user session successfully.")

            # 3. Select one topic from each Semester 5 subject
            target_subjects = [
                "Compiler Construction",
                "Operating Systems",
                "Machine Learning",
                "Web Engineering",
            ]

            print("=" * 70)
            print(" Running End-to-End Quiz Verification on SQLite (1 topic per subject)")
            print("=" * 70)

            for subject_name in target_subjects:
                topic = (
                    Topic.query.join(Course, Topic.course_id == Course.id)
                    .filter(Course.title == subject_name, Course.semester == 5)
                    .order_by(Topic.id)
                    .first()
                )
                assert topic is not None, f"No topic found for subject '{subject_name}' in Semester 5."

                print(f"\n--- Testing Subject: {subject_name} ---")
                print(f"Topic ID: {topic.id} | Name: {topic.name}")

                # Step A: GET /quiz/topic/<id>
                t0 = time.perf_counter()
                get_resp = client.get(f"/quiz/topic/{topic.id}")
                t_get = time.perf_counter() - t0

                assert get_resp.status_code == 200, f"GET /quiz/topic/{topic.id} failed with status {get_resp.status_code}"
                html = get_resp.get_data(as_text=True)
                assert "Questions for this topic are not added yet" not in html, "Unexpected empty quiz template."
                assert "Take Quiz:" in html or "Question" in html, "Expected quiz interface not rendered."
                print(f"  [GET /quiz/topic/{topic.id}] Status: {get_resp.status_code} | Latency: {t_get:.4f}s (< 1.0s: {t_get < 1.0})")
                assert t_get < 1.0, f"GET /quiz/topic/{topic.id} took too long: {t_get:.4f}s"

                # Step B: Prepare answer submission
                # Fetch questions served for this topic
                q_list = Question.query.filter_by(topic_id=topic.id).all()
                assert len(q_list) == 6, f"Expected 6 questions for topic {topic.id}, found {len(q_list)}"

                form_data = {}
                for q in q_list:
                    if q.type == "mcq":
                        form_data[f"question_{q.id}"] = q.correct_answer
                    elif q.type == "tf":
                        form_data[f"question_{q.id}"] = q.correct_answer
                    elif q.type == "short":
                        first_variant = q.correct_answer.split("|")[0].strip()
                        form_data[f"question_{q.id}"] = first_variant
                    elif q.type == "theory":
                        form_data[f"question_{q.id}"] = q.correct_answer

                # Step C: POST /quiz/topic/<id>/submit
                t0 = time.perf_counter()
                post_resp = client.post(
                    f"/quiz/topic/{topic.id}/submit",
                    data=form_data,
                    follow_redirects=False,
                )
                t_post = time.perf_counter() - t0

                assert post_resp.status_code == 302, f"POST /quiz/topic/{topic.id}/submit expected 302 redirect, got {post_resp.status_code}"
                redirect_url = post_resp.headers.get("Location")
                assert redirect_url is not None and "/quiz/attempt/" in redirect_url
                print(f"  [POST /quiz/topic/{topic.id}/submit] Status: {post_resp.status_code} -> Redirect: {redirect_url} | Latency: {t_post:.4f}s (< 1.0s: {t_post < 1.0})")
                assert t_post < 1.0, f"POST /quiz/topic/{topic.id}/submit took too long: {t_post:.4f}s"

                # Step D: GET /quiz/attempt/<attempt_id>
                t0 = time.perf_counter()
                result_resp = client.get(redirect_url)
                t_result = time.perf_counter() - t0

                assert result_resp.status_code == 200, f"GET {redirect_url} failed with status {result_resp.status_code}"
                result_html = result_resp.get_data(as_text=True)
                assert "Quiz Result" in result_html or "Attempt Summary" in result_html or "Score" in result_html or "Mastery" in result_html
                print(f"  [GET {redirect_url}] Status: {result_resp.status_code} | Latency: {t_result:.4f}s (< 1.0s: {t_result < 1.0})")
                assert t_result < 1.0, f"GET {redirect_url} took too long: {t_result:.4f}s"

            print("\n" + "=" * 70)
            print(" All 4 subject quizzes completed successfully with < 1.0s latencies!")
            print("=" * 70)

        finally:
            # Clean up: delete attempts and the temporary user
            Attempt.query.filter_by(user_id=user_id).delete()
            u = db.session.get(User, user_id)
            if u:
                db.session.delete(u)
            db.session.commit()
            print(f"> Deleted temporary test user (ID: {user_id}) and all associated attempts.")


if __name__ == "__main__":
    verify_quiz_flow()
