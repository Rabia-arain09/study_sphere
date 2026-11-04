"""Unit tests for the improvement rule in ml/improvement.py."""

from __future__ import annotations

import pytest
from app.models.attempt import MasteryLabel
from ml.improvement import apply_improvement_rule, IMPROVEMENT_THRESHOLD


# ---------------------------------------------------------------------------
# 1. Improvement of exactly the threshold (0.2) → label promoted one level
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "current_ratio, previous_ratio, model_label, expected",
    [
        # Weak → Good at exact threshold
        (0.70, 0.50, MasteryLabel.WEAK, MasteryLabel.GOOD),
        # Good → Better at exact threshold
        (0.90, 0.70, MasteryLabel.GOOD, MasteryLabel.BETTER),
        # Better → Excellent at exact threshold
        (1.00, 0.80, MasteryLabel.BETTER, MasteryLabel.EXCELLENT),
    ],
)
def test_improvement_exactly_threshold_promotes_one_level(
    current_ratio: float,
    previous_ratio: float,
    model_label: MasteryLabel,
    expected: MasteryLabel,
) -> None:
    """A gain of exactly 0.2 triggers a one-level promotion."""
    gain = current_ratio - previous_ratio
    assert abs(gain - IMPROVEMENT_THRESHOLD) < 1e-9, (
        f"Test setup error: expected gain={IMPROVEMENT_THRESHOLD}, got {gain}"
    )
    result = apply_improvement_rule(current_ratio, previous_ratio, model_label)
    assert result == expected


# ---------------------------------------------------------------------------
# 2. Improvement below the threshold → label unchanged
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "current_ratio, previous_ratio, model_label",
    [
        # Gain of 0.19 (just below threshold)
        (0.69, 0.50, MasteryLabel.WEAK),
        (0.89, 0.70, MasteryLabel.GOOD),
        # Gain of 0.0 (no change at all)
        (0.60, 0.60, MasteryLabel.GOOD),
        # Gain of 0.10 (half of threshold)
        (0.80, 0.70, MasteryLabel.BETTER),
    ],
)
def test_small_improvement_keeps_label(
    current_ratio: float,
    previous_ratio: float,
    model_label: MasteryLabel,
) -> None:
    """An improvement smaller than the threshold leaves the label unchanged."""
    result = apply_improvement_rule(current_ratio, previous_ratio, model_label)
    assert result == model_label


# ---------------------------------------------------------------------------
# 3. First attempt (previous_ratio == -1.0) → label always unchanged
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "current_ratio, model_label",
    [
        (0.0, MasteryLabel.WEAK),
        (0.6, MasteryLabel.GOOD),
        (0.8, MasteryLabel.BETTER),
        (1.0, MasteryLabel.EXCELLENT),
    ],
)
def test_first_attempt_label_unchanged(
    current_ratio: float,
    model_label: MasteryLabel,
) -> None:
    """First attempts (previous_ratio=-1.0) are always returned unchanged."""
    result = apply_improvement_rule(current_ratio, -1.0, model_label)
    assert result == model_label


# ---------------------------------------------------------------------------
# 4. Excellent cap – already at Excellent, cannot go higher
# ---------------------------------------------------------------------------


def test_excellent_cap_cannot_be_exceeded() -> None:
    """A student already labelled Excellent stays Excellent regardless of gain."""
    # Improvement of 0.5 (well above threshold), but already Excellent
    result = apply_improvement_rule(1.0, 0.5, MasteryLabel.EXCELLENT)
    assert result == MasteryLabel.EXCELLENT


# ---------------------------------------------------------------------------
# 5. Score drop (negative improvement) → label unchanged
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "current_ratio, previous_ratio, model_label",
    [
        # Score fell from 0.9 to 0.6
        (0.60, 0.90, MasteryLabel.GOOD),
        # Score fell from 1.0 to 0.5
        (0.50, 1.00, MasteryLabel.WEAK),
    ],
)
def test_score_drop_does_not_lower_label(
    current_ratio: float,
    previous_ratio: float,
    model_label: MasteryLabel,
) -> None:
    """A drop in score never causes the improvement rule to lower the label."""
    result = apply_improvement_rule(current_ratio, previous_ratio, model_label)
    # Rule must not lower the label below the model's label
    assert result == model_label
