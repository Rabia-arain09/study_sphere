"""Improvement rule for mastery label post-processing.

Adjusts a Decision Tree mastery label upward by one tier when a student
demonstrates clear improvement (≥ 0.2 score-ratio gain) over their previous
attempt on the same topic.  First attempts are always returned unchanged, and
no label is ever lowered or promoted past *Excellent*.
"""

from __future__ import annotations

from app.models.attempt import MasteryLabel

# Ordered promotion chain: index i can be promoted to index i+1.
_LABEL_ORDER: list[MasteryLabel] = [
    MasteryLabel.WEAK,
    MasteryLabel.GOOD,
    MasteryLabel.BETTER,
    MasteryLabel.EXCELLENT,
]

#: Minimum score-ratio gain required to trigger a one-level label promotion.
IMPROVEMENT_THRESHOLD: float = 0.2


def apply_improvement_rule(
    current_ratio: float,
    previous_ratio: float,
    model_label: MasteryLabel,
) -> MasteryLabel:
    """Return an adjusted mastery label that rewards clear score-ratio improvement.

    If the student's current score ratio is at least
    :data:`IMPROVEMENT_THRESHOLD` higher than their previous attempt ratio,
    the label is promoted by **one tier** (e.g. Weak → Good).  The rule
    never lowers a label and cannot exceed *Excellent*.

    For first attempts (indicated by ``previous_ratio == -1.0`` per the ML
    pipeline convention), the original ``model_label`` is returned unchanged.

    Args:
        current_ratio: Score ratio of the current attempt (score / total_questions),
            in the range [0.0, 1.0].
        previous_ratio: Score ratio of the immediately preceding attempt by the
            same user on the same topic, or ``-1.0`` when no prior attempt exists.
        model_label: The mastery label produced by the Decision Tree classifier.

    Returns:
        MasteryLabel: The original ``model_label`` if no improvement threshold
        is met, or the next-higher label if the threshold is satisfied and the
        current label is not already *Excellent*.
    """
    # First attempt – sentinel value used throughout the ML pipeline
    if previous_ratio < 0.0:
        return model_label

    improvement = current_ratio - previous_ratio
    if improvement < IMPROVEMENT_THRESHOLD - 1e-9:
        return model_label

    # Find current position in the promotion chain
    try:
        idx = _LABEL_ORDER.index(model_label)
    except ValueError:
        # Unknown label: return as-is (defensive – should not happen in practice)
        return model_label

    # Promote by one level, capped at Excellent
    next_idx = min(idx + 1, len(_LABEL_ORDER) - 1)
    return _LABEL_ORDER[next_idx]
