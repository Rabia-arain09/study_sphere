"""Verification script for Phase 3: Content-based topic recommender.

Measures route response latency on SQLite, prints top 5 related topics for
sample topics across three distinct curriculum subjects (Machine Learning,
Operating Systems, and Compiler Construction), and verifies <1s response constraint.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Any

# Ensure repository root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Safe Windows stdout encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app import create_app
from app.extensions import db
from app.models.topic import Topic
from app.models.user import User
from app.services.recommendation_service import reset_recommender, get_related_topics


def run_verification():
    """Execute complete recommender verification on SQLite."""
    reset_recommender()
    app = create_app("development")

    with app.app_context():
        dialect_name = db.engine.dialect.name
        print("=" * 80)
        print(f" RECOMMENDER VERIFICATION ON {dialect_name.upper()}")
        print("=" * 80)

        # 1. Setup temporary test user for authentication
        test_email = "recommender_verifier@example.com"
        existing = User.query.filter_by(email=test_email).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()

        temp_user = User(
            name="Verification Student",
            email=test_email,
            semester=5,
        )
        temp_user.set_password("VerifyPass123!")
        db.session.add(temp_user)
        db.session.commit()

        # 2. Select 3 sample topics: Machine Learning, Operating Systems, Compiler Construction
        ml_topic = (
            Topic.query.filter(Topic.subject.ilike("%Machine Learning%"))
            .order_by(Topic.id)
            .first()
        )
        os_topic = (
            Topic.query.filter(Topic.subject.ilike("%Operating Systems%"))
            .order_by(Topic.id)
            .first()
        )
        compiler_topic = (
            Topic.query.filter(Topic.subject.ilike("%Compiler%"))
            .order_by(Topic.id)
            .first()
        )

        assert ml_topic is not None, "ML topic not found in database"
        assert os_topic is not None, "OS topic not found in database"
        assert compiler_topic is not None, "Compiler topic not found in database"

        sample_topics = [
            ("Machine Learning", ml_topic),
            ("Operating Systems", os_topic),
            ("Compiler Construction", compiler_topic),
        ]

        try:
            with app.test_client() as client:
                # 3. Authenticate
                get_login = client.get("/auth/login")
                csrf_match = re.search(
                    r'name="csrf_token"\s+type="hidden"\s+value="([^"]+)"',
                    get_login.data.decode("utf-8", errors="replace"),
                ) or re.search(
                    r'value="([^"]+)"\s+name="csrf_token"',
                    get_login.data.decode("utf-8", errors="replace"),
                )
                csrf_token = csrf_match.group(1) if csrf_match else ""

                login_res = client.post(
                    "/auth/login",
                    data={
                        "csrf_token": csrf_token,
                        "email": test_email,
                        "password": "VerifyPass123!",
                    },
                    follow_redirects=True,
                )
                assert login_res.status_code == 200, "Authentication failed"

                print("\n[1] TOP 5 RELATED TOPICS FOR SAMPLE TOPICS:")
                print("-" * 80)

                for domain_label, topic in sample_topics:
                    print(f"\n--- Target Topic #{topic.id}: \"{topic.name}\" ({domain_label}) ---")
                    related = get_related_topics(topic.id, k=5)
                    if not related:
                        print("    (No recommendations found)")
                    for rank, rel in enumerate(related, start=1):
                        pct = round(rel["score"] * 100, 1)
                        print(
                            f"    {rank}. [ID {rel['id']:3d}] {rel['name']} "
                            f"| Course: {rel['course']} | Wk {rel['week']} | "
                            f"Diff: {rel['difficulty']}/5 | Score: {rel['score']:.4f} ({pct}%)"
                        )

                print("\n" + "=" * 80)
                print("[2] ROUTE TIMING MEASUREMENTS (< 1.0s requirement):")
                print("=" * 80)

                # Reset recommender before timing to accurately measure cold first call
                reset_recommender()

                timing_records = []

                for domain_label, topic in sample_topics:
                    # Timing /topics/<id>/related (first call)
                    t0 = time.perf_counter()
                    res_rel_1 = client.get(f"/topics/{topic.id}/related")
                    t_rel_1 = (time.perf_counter() - t0) * 1000

                    # Timing /topics/<id>/related (cached call)
                    t0 = time.perf_counter()
                    res_rel_2 = client.get(f"/topics/{topic.id}/related")
                    t_rel_2 = (time.perf_counter() - t0) * 1000

                    # Timing /topics/<id> (first call)
                    t0 = time.perf_counter()
                    res_page_1 = client.get(f"/topics/{topic.id}")
                    t_page_1 = (time.perf_counter() - t0) * 1000

                    # Timing /topics/<id> (cached call)
                    t0 = time.perf_counter()
                    res_page_2 = client.get(f"/topics/{topic.id}")
                    t_page_2 = (time.perf_counter() - t0) * 1000

                    assert res_rel_1.status_code == 200
                    assert res_rel_2.status_code == 200
                    assert res_page_1.status_code == 200
                    assert res_page_2.status_code == 200

                    timing_records.append({
                        "domain": domain_label,
                        "topic_id": topic.id,
                        "topic_name": topic.name,
                        "rel_first_ms": t_rel_1,
                        "rel_cached_ms": t_rel_2,
                        "page_first_ms": t_page_1,
                        "page_cached_ms": t_page_2,
                    })

                print(
                    f"{'Topic (Domain)':<35} | {'/related (1st)':<14} | {'/related (2nd)':<14} | "
                    f"{'Page (1st)':<12} | {'Page (2nd)':<12} | Status"
                )
                print("-" * 105)

                all_under_1s = True
                for rec in timing_records:
                    topic_str = f"#{rec['topic_id']} {rec['domain']}"
                    rel1_str = f"{rec['rel_first_ms']:.2f} ms"
                    rel2_str = f"{rec['rel_cached_ms']:.2f} ms"
                    page1_str = f"{rec['page_first_ms']:.2f} ms"
                    page2_str = f"{rec['page_cached_ms']:.2f} ms"

                    max_t = max(rec["rel_first_ms"], rec["rel_cached_ms"], rec["page_first_ms"], rec["page_cached_ms"])
                    pass_fail = "PASS (<1s)" if max_t < 1000 else "FAIL"
                    if max_t >= 1000:
                        all_under_1s = False

                    print(
                        f"{topic_str:<35} | {rel1_str:<14} | {rel2_str:<14} | "
                        f"{page1_str:<12} | {page2_str:<12} | {pass_fail}"
                    )

                print("-" * 105)
                print(f"Latency Constraint Check (< 1.0s): {'ALL PASSED' if all_under_1s else 'FAILED'}")

        finally:
            # Clean up temporary test user
            u = User.query.filter_by(email=test_email).first()
            if u:
                db.session.delete(u)
                db.session.commit()


if __name__ == "__main__":
    run_verification()
