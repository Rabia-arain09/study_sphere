"""Validation script for StudySphere assessment question bank CSV files.

Verifies schema, referential integrity against curriculum topics,
per-topic question type quotas (3 MCQ, 1 TF, 1 Short, 1 Theory),
option completeness, answer constraints, and MCQ letter balance.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

EXPECTED_SUBJECT_FILES: dict[str, str] = {
    "Compiler Construction": "compiler-construction.csv",
    "Machine Learning": "machine-learning.csv",
    "Operating Systems": "operating-systems.csv",
    "Web Engineering": "web-engineering.csv",
}

REQUIRED_COLUMNS: list[str] = [
    "semester",
    "subject",
    "topic",
    "type",
    "question_text",
    "option_a",
    "option_b",
    "option_c",
    "option_d",
    "correct_answer",
    "source",
]

VALID_QUESTION_TYPES: set[str] = {"mcq", "tf", "short", "theory"}


@dataclass
class SubjectValidationStats:
    """Statistics collected for a single subject's question bank."""

    subject_name: str
    total_questions: int = 0
    topic_count: int = 0
    type_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    mcq_letter_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))


@dataclass
class ValidationReport:
    """Aggregated validation findings across all question files."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    subject_stats: dict[str, SubjectValidationStats] = field(default_factory=dict)
    total_questions: int = 0
    total_topics: int = 0

    def print_summary(self) -> None:
        """Print a structured summary of the validation results to stdout."""
        print("=" * 70)
        print(" StudySphere Question Bank Validation Summary")
        print("=" * 70)
        print(f"> Status           : {'PASSED' if self.is_valid else 'FAILED'}")
        print(f"> Total Questions  : {self.total_questions} (expected: 990)")
        print(f"> Total Topics     : {self.total_topics} (expected: 165)")
        print(f"> Error Count      : {len(self.errors)}")
        print(f"> Warning Count    : {len(self.warnings)}")
        print("-" * 70)

        for subj, stats in sorted(self.subject_stats.items()):
            print(f"Subject: {subj}")
            print(f"  Topics covered   : {stats.topic_count}")
            print(f"  Total questions  : {stats.total_questions}")
            print(
                f"  Type breakdown   : mcq={stats.type_counts.get('mcq', 0)}, "
                f"tf={stats.type_counts.get('tf', 0)}, "
                f"short={stats.type_counts.get('short', 0)}, "
                f"theory={stats.type_counts.get('theory', 0)}"
            )
            mcq_total = stats.type_counts.get("mcq", 0)
            if mcq_total > 0:
                dist_str = ", ".join(
                    f"{letter}: {cnt} ({cnt / mcq_total * 100:.1f}%)"
                    for letter, cnt in sorted(stats.mcq_letter_counts.items())
                )
                print(f"  MCQ distribution : {dist_str}")
            print()

        if self.errors:
            print("=" * 70)
            print(f"Validation Errors ({len(self.errors)}):")
            print("=" * 70)
            for err in self.errors[:50]:
                print(f"  - {err}")
            if len(self.errors) > 50:
                print(f"  ... and {len(self.errors) - 50} more errors.")

        if self.warnings:
            print("=" * 70)
            print(f"Validation Warnings ({len(self.warnings)}):")
            print("=" * 70)
            for warn in self.warnings[:30]:
                print(f"  - {warn}")
            if len(self.warnings) > 30:
                print(f"  ... and {len(self.warnings) - 30} more warnings.")
        print("=" * 70)


def count_sentences(text: str) -> int:
    """Heuristic to count sentences in a theory model answer.

    Args:
        text: The model answer text.

    Returns:
        int: Number of detected sentences (minimum 1 for non-empty text).
    """
    clean = text.strip()
    if not clean:
        return 0
    # Split on period, exclamation, or question mark followed by space or end of string
    raw_sentences = re.split(r"[.!?]+(?:\s+|$)", clean)
    sentences = [s.strip() for s in raw_sentences if s.strip()]
    return max(len(sentences), 1)


def validate_questions_bank(
    questions_dir: Path | str = "data/questions",
    topics_csv_path: Path | str = "data/topics.csv",
) -> ValidationReport:
    """Validate all question bank CSV files against curriculum rules and constraints.

    Args:
        questions_dir: Directory containing per-subject question CSV files.
        topics_csv_path: Path to canonical curriculum topics CSV.

    Returns:
        ValidationReport: Aggregated validation report with errors and metrics.
    """
    q_dir = Path(questions_dir)
    top_path = Path(topics_csv_path)

    errors: list[str] = []
    warnings: list[str] = []

    # 1. Verify existence of topics.csv and load Semester 5 topics
    if not top_path.exists():
        errors.append(f"Curriculum topics file not found at '{top_path}'.")
        return ValidationReport(is_valid=False, errors=errors)

    sem5_topics_by_subject: dict[str, list[str]] = defaultdict(list)
    try:
        with open(top_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sem = row.get("semester", "").strip()
                if sem == "5":
                    subj = row.get("subject", "").strip()
                    topic = row.get("topic", "").strip()
                    sem5_topics_by_subject[subj].append(topic)
    except Exception as exc:
        errors.append(f"Failed to read topics CSV at '{top_path}': {exc}")
        return ValidationReport(is_valid=False, errors=errors)

    # 2. Verify directory existence
    if not q_dir.exists() or not q_dir.is_dir():
        errors.append(f"Questions directory '{q_dir}' does not exist or is not a directory.")
        return ValidationReport(is_valid=False, errors=errors)

    seen_question_texts: dict[str, str] = {}
    subject_stats: dict[str, SubjectValidationStats] = {}
    total_validated_topics = 0
    total_validated_questions = 0

    # 3. Validate each subject file
    for subj_name, filename in EXPECTED_SUBJECT_FILES.items():
        file_path = q_dir / filename
        stats = SubjectValidationStats(subject_name=subj_name)
        subject_stats[subj_name] = stats

        if not file_path.exists():
            errors.append(f"Expected questions file '{file_path}' is missing.")
            continue

        expected_topics = sem5_topics_by_subject.get(subj_name, [])
        expected_topics_set = set(expected_topics)

        # Track questions by topic: topic -> type -> list[rows]
        topic_questions: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(
            lambda: defaultdict(list)
        )

        try:
            with open(file_path, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                fieldnames = [c.strip().lower() for c in (reader.fieldnames or [])]

                missing_cols = [c for c in REQUIRED_COLUMNS if c not in fieldnames]
                if missing_cols:
                    errors.append(
                        f"[{filename}] CSV header missing required column(s): {', '.join(missing_cols)}"
                    )
                    continue

                for row_idx, raw_row in enumerate(reader, start=2):
                    row = {
                        k.strip().lower(): (v.strip() if v else "")
                        for k, v in raw_row.items()
                        if k is not None
                    }

                    stats.total_questions += 1
                    total_validated_questions += 1

                    # Required non-empty common fields
                    sem = row.get("semester", "")
                    subj = row.get("subject", "")
                    topic = row.get("topic", "")
                    q_type = row.get("type", "").lower()
                    q_text = row.get("question_text", "")
                    correct_ans = row.get("correct_answer", "")
                    source = row.get("source", "").lower()

                    if sem != "5":
                        errors.append(
                            f"[{filename}:row {row_idx}] 'semester' must be '5' (got '{sem}')."
                        )

                    if subj != subj_name:
                        errors.append(
                            f"[{filename}:row {row_idx}] 'subject' must match '{subj_name}' (got '{subj}')."
                        )

                    if not topic:
                        errors.append(f"[{filename}:row {row_idx}] 'topic' cannot be empty.")
                    elif topic not in expected_topics_set:
                        errors.append(
                            f"[{filename}:row {row_idx}] Unknown topic '{topic}' for subject '{subj_name}'."
                        )

                    if q_type not in VALID_QUESTION_TYPES:
                        errors.append(
                            f"[{filename}:row {row_idx}] Invalid question type '{q_type}'. "
                            f"Must be one of: {sorted(VALID_QUESTION_TYPES)}."
                        )
                    else:
                        stats.type_counts[q_type] += 1

                    if not q_text:
                        errors.append(f"[{filename}:row {row_idx}] 'question_text' cannot be empty.")
                    else:
                        # Global uniqueness check
                        norm_text = re.sub(r"\s+", " ", q_text.strip().lower())
                        loc = f"{filename}:row {row_idx}"
                        if norm_text in seen_question_texts:
                            errors.append(
                                f"[{loc}] Duplicate question text already found in [{seen_question_texts[norm_text]}]: "
                                f"'{q_text[:60]}...'"
                            )
                        else:
                            seen_question_texts[norm_text] = loc

                    if source != "generated":
                        errors.append(
                            f"[{filename}:row {row_idx}] 'source' must be 'generated' (got '{source}')."
                        )

                    if not correct_ans:
                        errors.append(f"[{filename}:row {row_idx}] 'correct_answer' cannot be empty.")

                    # Type-specific rules
                    if q_type == "mcq":
                        opt_a = row.get("option_a", "")
                        opt_b = row.get("option_b", "")
                        opt_c = row.get("option_c", "")
                        opt_d = row.get("option_d", "")

                        if not opt_a or not opt_b or not opt_c or not opt_d:
                            errors.append(
                                f"[{filename}:row {row_idx}] MCQ questions must have 4 non-empty options."
                            )

                        if correct_ans.upper() not in {"A", "B", "C", "D"}:
                            errors.append(
                                f"[{filename}:row {row_idx}] MCQ correct_answer must be 'A', 'B', 'C', or 'D' "
                                f"(got '{correct_ans}')."
                            )
                        else:
                            stats.mcq_letter_counts[correct_ans.upper()] += 1

                        # Plausible distractor rule: avoid trivial giveaways
                        for opt_name, opt_val in [
                            ("option_a", opt_a),
                            ("option_b", opt_b),
                            ("option_c", opt_c),
                            ("option_d", opt_d),
                        ]:
                            low_val = opt_val.lower()
                            if "all of the above" in low_val or "none of the above" in low_val:
                                errors.append(
                                    f"[{filename}:row {row_idx}] MCQ {opt_name} must avoid lazy distractors "
                                    f"like 'all/none of the above' (got '{opt_val}')."
                                )

                    elif q_type == "tf":
                        if correct_ans not in {"True", "False"}:
                            errors.append(
                                f"[{filename}:row {row_idx}] TF correct_answer must be 'True' or 'False' "
                                f"(got '{correct_ans}')."
                            )
                        opt_a = row.get("option_a", "")
                        opt_b = row.get("option_b", "")
                        if opt_a != "True" or opt_b != "False":
                            warnings.append(
                                f"[{filename}:row {row_idx}] TF option_a should be 'True' and option_b 'False' "
                                f"(got '{opt_a}', '{opt_b}')."
                            )

                    elif q_type == "short":
                        # Short answers should have 1 to 3 words per variant
                        variants = [v.strip() for v in correct_ans.split("|") if v.strip()]
                        if not variants:
                            errors.append(
                                f"[{filename}:row {row_idx}] Short answer correct_answer must contain at least one variant."
                            )
                        for var in variants:
                            word_count = len(var.split())
                            if word_count > 4:
                                warnings.append(
                                    f"[{filename}:row {row_idx}] Short answer variant '{var}' has {word_count} words "
                                    f"(recommended: 1 to 3 words)."
                                )

                    elif q_type == "theory":
                        s_count = count_sentences(correct_ans)
                        if s_count < 2 or s_count > 5:
                            warnings.append(
                                f"[{filename}:row {row_idx}] Theory model answer has {s_count} sentences "
                                f"(target: 2 to 4 sentences)."
                            )

                    if topic and q_type in VALID_QUESTION_TYPES:
                        topic_questions[topic][q_type].append(row)

        except Exception as exc:
            errors.append(f"[{filename}] Failed to read or parse file: {exc}")
            continue

        # Check coverage and quotas for all expected topics
        stats.topic_count = len(topic_questions)
        total_validated_topics += stats.topic_count

        missing_topics = [t for t in expected_topics if t not in topic_questions]
        if missing_topics:
            errors.append(
                f"[{filename}] Missing all questions for {len(missing_topics)} topic(s): "
                f"{', '.join(missing_topics[:5])}"
            )

        for top_name in expected_topics:
            t_qs = topic_questions.get(top_name, {})
            mcq_cnt = len(t_qs.get("mcq", []))
            tf_cnt = len(t_qs.get("tf", []))
            short_cnt = len(t_qs.get("short", []))
            theory_cnt = len(t_qs.get("theory", []))

            if mcq_cnt != 3:
                errors.append(
                    f"[{filename}] Topic '{top_name}' has {mcq_cnt} MCQ questions (expected: 3)."
                )
            if tf_cnt != 1:
                errors.append(
                    f"[{filename}] Topic '{top_name}' has {tf_cnt} TF questions (expected: 1)."
                )
            if short_cnt != 1:
                errors.append(
                    f"[{filename}] Topic '{top_name}' has {short_cnt} Short questions (expected: 1)."
                )
            if theory_cnt != 1:
                errors.append(
                    f"[{filename}] Topic '{top_name}' has {theory_cnt} Theory questions (expected: 1)."
                )

        # MCQ correct answer letter balance check for the subject
        mcq_total = stats.type_counts.get("mcq", 0)
        if mcq_total > 0:
            expected_per_letter = mcq_total / 4.0
            for letter in ["A", "B", "C", "D"]:
                cnt = stats.mcq_letter_counts.get(letter, 0)
                pct = cnt / mcq_total
                # Flag if any letter is severely imbalanced (< 15% or > 35%)
                if pct < 0.15 or pct > 0.35:
                    warnings.append(
                        f"[{filename}] MCQ correct_answer '{letter}' has count {cnt} ({pct * 100:.1f}%), "
                        f"which deviates significantly from 25%."
                    )

    is_valid = len(errors) == 0
    return ValidationReport(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        subject_stats=subject_stats,
        total_questions=total_validated_questions,
        total_topics=total_validated_topics,
    )


def main() -> int:
    """CLI entrypoint for running question bank validation."""
    report = validate_questions_bank()
    report.print_summary()
    return 0 if report.is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
