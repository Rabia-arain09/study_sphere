"""Per-attempt and aggregate topic mastery Decision Tree models for StudySphere.

The per-attempt classifier uses:
- score_ratio (score / total_questions)
- wrong_ratio (wrong_count / total_questions)
- total_questions
- attempt_number (capped at 5)
- previous_score_ratio (-1.0 if first attempt)
- improvement (score_ratio - previous_score_ratio, 0.0 if none)

The topic classifier uses aggregate features from all attempts on one topic:
average score ratio, latest score ratio, best score ratio, attempt count, and trend.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
import joblib
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.tree import DecisionTreeClassifier, export_text

logger = logging.getLogger(__name__)

FEATURE_NAMES: list[str] = [
    "score_ratio",
    "wrong_ratio",
    "total_questions",
    "attempt_number",
    "previous_score_ratio",
    "improvement",
]

LABELS: list[str] = ["Weak", "Good", "Better", "Excellent"]

# Canonical file paths
REPO_ROOT: Path = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_DIR: Path = REPO_ROOT / "ml" / "models"
DEFAULT_MODEL_PATH: Path = DEFAULT_MODEL_DIR / "label_model.joblib"
DEFAULT_REPORTS_DIR: Path = REPO_ROOT / "ml" / "reports"
DEFAULT_METRICS_PATH: Path = DEFAULT_REPORTS_DIR / "label_model_metrics.json"
DEFAULT_TREE_PATH: Path = DEFAULT_REPORTS_DIR / "label_tree.txt"
TOPIC_FEATURE_NAMES: list[str] = [
    "average_score_ratio",
    "latest_score_ratio",
    "best_score_ratio",
    "attempt_count",
    "trend",
]
DEFAULT_TOPIC_MODEL_PATH: Path = DEFAULT_MODEL_DIR / "topic_label_model.joblib"
DEFAULT_TOPIC_METRICS_PATH: Path = (
    DEFAULT_REPORTS_DIR / "topic_label_model_metrics.json"
)
DEFAULT_TOPIC_TREE_PATH: Path = DEFAULT_REPORTS_DIR / "topic_label_tree.txt"


def generate_synthetic_dataset(
    n: int = 1000,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate reproducible synthetic attempt dataset reflecting realistic quiz records.

    Rules applied:
    - total_questions: random choice from [4, 5, 6].
    - score: steps of 0.5 points between 0.0 and total_questions (due to theory half-points).
    - wrong_count: total_questions - score.
    - attempt_number: 1 to 8 (feature is capped at 5).
    - previous_score_ratio: -1.0 if attempt 1; else previous score ratio in [0.0, 1.0].
    - improvement: score_ratio - previous_score_ratio (0.0 if attempt 1).

    Label rules on score_ratio:
    - score_ratio < 0.5: Weak
    - 0.5 <= score_ratio < 0.7: Good
    - 0.7 <= score_ratio < 0.9: Better
    - score_ratio >= 0.9: Excellent

    Attempt history rule:
    - Repeated Weak: if attempt_number >= 3, previous attempt was Weak (< 0.5), and current
      score_ratio is at the boundary edge (0.50 to < 0.55), the student remains "Weak"
      to reflect persistent conceptual difficulty.
    - First-attempt high performers: score >= 0.9 on attempt 1 remains "Excellent".

    Boundary noise:
    - Approximately 5% label noise is applied only to instances within +/-0.03 of decision
      boundaries (0.5, 0.7, 0.9), preventing trivially perfect artificial classification
      while maintaining >85% realistic test performance.

    Args:
        n: Total number of synthetic samples to generate.
        seed: Random seed for reproducibility.

    Returns:
        tuple[np.ndarray, np.ndarray]: Feature matrix X (n, 6) and target labels y (n,).
    """
    rng = np.random.default_rng(seed)
    X_rows: list[list[float]] = []
    y_labels: list[str] = []

    for _ in range(n):
        total_q = int(rng.integers(4, 7))  # 4, 5, or 6 questions
        # Possible scores in increments of 0.5
        possible_scores = np.arange(0.0, total_q + 0.1, 0.5)
        score = float(rng.choice(possible_scores))
        wrong_count = float(total_q - score)

        score_ratio = float(score / total_q)
        wrong_ratio = float(wrong_count / total_q)

        raw_attempt_num = int(rng.integers(1, 9))  # 1 to 8
        attempt_number = min(raw_attempt_num, 5)

        if raw_attempt_num == 1:
            prev_score_ratio = -1.0
            improvement = 0.0
        else:
            prev_total_q = int(rng.integers(4, 7))
            prev_possible = np.arange(0.0, prev_total_q + 0.1, 0.5)
            prev_score = float(rng.choice(prev_possible))
            prev_score_ratio = float(prev_score / prev_total_q)
            improvement = float(score_ratio - prev_score_ratio)

        # Baseline rule-based classification
        if score_ratio < 0.5:
            label = "Weak"
        elif score_ratio < 0.7:
            label = "Good"
        elif score_ratio < 0.9:
            label = "Better"
        else:
            label = "Excellent"

        # Attempt history rule: repeated weak across 3+ attempts stays Weak at edge
        if raw_attempt_num >= 3 and 0.0 <= prev_score_ratio < 0.5:
            if 0.5 <= score_ratio < 0.55:
                label = "Weak"

        # Approximately 5% label noise only in close proximity (+/- 0.03) to boundaries
        boundary_hit = None
        for boundary in (0.5, 0.7, 0.9):
            if abs(score_ratio - boundary) <= 0.03:
                boundary_hit = boundary
                break

        if boundary_hit is not None and rng.random() < 0.05:
            if boundary_hit == 0.5:
                label = "Good" if label == "Weak" else "Weak"
            elif boundary_hit == 0.7:
                label = "Better" if label == "Good" else "Good"
            elif boundary_hit == 0.9:
                label = "Better" if label == "Excellent" else "Excellent"

        X_rows.append([
            score_ratio,
            wrong_ratio,
            float(total_q),
            float(attempt_number),
            prev_score_ratio,
            improvement,
        ])
        y_labels.append(label)

    return np.array(X_rows, dtype=float), np.array(y_labels, dtype=object)


def train_model(
    dataset: tuple[np.ndarray, np.ndarray] | None = None,
    seed: int = 42,
    model_path: Path | str | None = None,
    metrics_path: Path | str | None = None,
    tree_path: Path | str | None = None,
) -> dict[str, Any]:
    """Train the Decision Tree classifier using stratified cross-validation and hyperparameter tuning.

    Evaluates criterion ('gini' vs 'entropy') and max_depth (2 to 8) via 5-fold cross-validation
    on an 80% training split. Retrains the optimal estimator, evaluates on the 20% holdout test set,
    persists the model to joblib, and writes metrics JSON and tree text reports.

    Args:
        dataset: Optional pre-generated (X, y) tuple. If None, generated via generate_synthetic_dataset().
        seed: Random seed for data generation, CV partitioning, and model training.
        model_path: Destination path for joblib model file (default: ml/models/label_model.joblib).
        metrics_path: Destination path for metrics JSON (default: ml/reports/label_model_metrics.json).
        tree_path: Destination path for tree text export (default: ml/reports/label_tree.txt).

    Returns:
        dict[str, Any]: Comprehensive evaluation report including train/test accuracies,
            best hyperparameters, per-class metrics, confusion matrix, and feature importances.
    """
    if dataset is None:
        X, y = generate_synthetic_dataset(n=1000, seed=seed)
    else:
        X, y = dataset

    # Stratified 80/20 train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=seed,
        stratify=y,
    )

    # 5-fold Stratified Cross-Validation over criterion and max_depth 2 to 8
    param_grid = {
        "criterion": ["gini", "entropy"],
        "max_depth": list(range(2, 9)),
    }
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    grid_search = GridSearchCV(
        estimator=DecisionTreeClassifier(random_state=seed),
        param_grid=param_grid,
        cv=cv,
        scoring="accuracy",
        refit=True,
    )
    grid_search.fit(X_train, y_train)

    best_model: DecisionTreeClassifier = grid_search.best_estimator_

    # Evaluate train vs test performance to transparently document generalization & overfitting
    train_pred = best_model.predict(X_train)
    test_pred = best_model.predict(X_test)

    train_acc = float(accuracy_score(y_train, train_pred))
    test_acc = float(accuracy_score(y_test, test_pred))

    report_dict = classification_report(
        y_test,
        test_pred,
        labels=LABELS,
        output_dict=True,
        zero_division=0,
    )
    report_text = classification_report(
        y_test,
        test_pred,
        labels=LABELS,
        zero_division=0,
    )

    cm = confusion_matrix(y_test, test_pred, labels=LABELS)
    cm_dict = {
        "labels": LABELS,
        "matrix": cm.tolist(),
    }

    feature_importances = dict(
        zip(FEATURE_NAMES, [round(float(v), 4) for v in best_model.feature_importances_])
    )

    # Serialize trained model artifact
    target_model_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
    target_model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_model, target_model_path)
    logger.info("Persisted Decision Tree model to %s", target_model_path)

    # Prepare and persist committed reports
    target_metrics_path = Path(metrics_path) if metrics_path else DEFAULT_METRICS_PATH
    target_metrics_path.parent.mkdir(parents=True, exist_ok=True)

    metrics_payload = {
        "model_type": "DecisionTreeClassifier",
        "best_params": grid_search.best_params_,
        "cv_best_score": round(float(grid_search.best_score_), 4),
        "train_accuracy": round(train_acc, 4),
        "test_accuracy": round(test_acc, 4),
        "feature_importances": feature_importances,
        "per_class_metrics": {
            label: {
                "precision": round(float(report_dict[label]["precision"]), 4),
                "recall": round(float(report_dict[label]["recall"]), 4),
                "f1_score": round(float(report_dict[label]["f1-score"]), 4),
                "support": int(report_dict[label]["support"]),
            }
            for label in LABELS
            if label in report_dict
        },
        "macro_avg": {
            "precision": round(float(report_dict["macro avg"]["precision"]), 4),
            "recall": round(float(report_dict["macro avg"]["recall"]), 4),
            "f1_score": round(float(report_dict["macro avg"]["f1-score"]), 4),
        },
        "confusion_matrix": cm_dict,
    }

    with open(target_metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_payload, f, indent=2)

    # Export human-readable ASCII decision tree
    target_tree_path = Path(tree_path) if tree_path else DEFAULT_TREE_PATH
    target_tree_path.parent.mkdir(parents=True, exist_ok=True)
    tree_text = export_text(best_model, feature_names=FEATURE_NAMES)
    with open(target_tree_path, "w", encoding="utf-8") as f:
        f.write(tree_text)

    return {
        "model": best_model,
        "best_params": grid_search.best_params_,
        "cv_best_score": float(grid_search.best_score_),
        "train_accuracy": train_acc,
        "test_accuracy": test_acc,
        "classification_report_str": report_text,
        "metrics": metrics_payload,
        "confusion_matrix": cm,
        "feature_importances": feature_importances,
        "tree_text": tree_text,
        "model_path": str(target_model_path),
        "metrics_path": str(target_metrics_path),
        "tree_path": str(target_tree_path),
    }


def generate_synthetic_topic_dataset(
    n: int = 1000,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate reproducible synthetic mastery features across topic attempt histories.

    Labels use a weighted score (40% average, 35% latest, 25% best), a 0.05 bonus
    for a positive trend or penalty for a negative trend, and small Gaussian noise.
    The weighted score maps to the four mastery tiers at 0.50, 0.70, and 0.90.

    Args:
        n: Number of synthetic user-topic histories.
        seed: Random seed for reproducibility.

    Returns:
        tuple[np.ndarray, np.ndarray]: Feature matrix (n, 5) and string labels.
    """
    rng = np.random.default_rng(seed)
    feature_rows: list[list[float]] = []
    labels: list[str] = []

    for _ in range(n):
        attempt_count = int(rng.integers(1, 9))
        underlying_score = float(rng.uniform(0.0, 1.0))
        ratios = np.clip(
            underlying_score + rng.normal(0.0, 0.18, size=attempt_count),
            0.0,
            1.0,
        )
        average_ratio = float(np.mean(ratios))
        latest_ratio = float(ratios[-1])
        best_ratio = float(np.max(ratios))
        trend = latest_ratio - average_ratio

        weighted_score = (
            0.40 * average_ratio
            + 0.35 * latest_ratio
            + 0.25 * best_ratio
            + (0.05 if trend > 0 else -0.05 if trend < 0 else 0.0)
            + float(rng.normal(0.0, 0.015))
        )
        if weighted_score < 0.50:
            label = "Weak"
        elif weighted_score < 0.70:
            label = "Good"
        elif weighted_score < 0.90:
            label = "Better"
        else:
            label = "Excellent"

        feature_rows.append([
            average_ratio,
            latest_ratio,
            best_ratio,
            float(attempt_count),
            trend,
        ])
        labels.append(label)

    return np.asarray(feature_rows, dtype=float), np.asarray(labels, dtype=object)


def train_topic_model(
    dataset: tuple[np.ndarray, np.ndarray] | None = None,
    seed: int = 42,
    model_path: Path | str | None = None,
    metrics_path: Path | str | None = None,
    tree_path: Path | str | None = None,
) -> dict[str, Any]:
    """Train and evaluate the fixed entropy, depth-5 topic mastery Decision Tree."""
    if dataset is None:
        X, y = generate_synthetic_topic_dataset(seed=seed)
    else:
        X, y = dataset

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=seed,
        stratify=y,
    )
    model = DecisionTreeClassifier(
        criterion="entropy",
        max_depth=5,
        random_state=seed,
    )
    model.fit(X_train, y_train)

    train_predictions = model.predict(X_train)
    test_predictions = model.predict(X_test)
    train_accuracy = float(accuracy_score(y_train, train_predictions))
    test_accuracy = float(accuracy_score(y_test, test_predictions))
    report = classification_report(
        y_test,
        test_predictions,
        labels=LABELS,
        output_dict=True,
        zero_division=0,
    )
    report_text = classification_report(
        y_test,
        test_predictions,
        labels=LABELS,
        zero_division=0,
    )
    matrix = confusion_matrix(y_test, test_predictions, labels=LABELS)
    feature_importances = dict(
        zip(
            TOPIC_FEATURE_NAMES,
            [round(float(value), 4) for value in model.feature_importances_],
        )
    )

    target_model_path = Path(model_path) if model_path else DEFAULT_TOPIC_MODEL_PATH
    target_model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, target_model_path)

    metrics_payload = {
        "model_type": "DecisionTreeClassifier",
        "best_params": {"criterion": "entropy", "max_depth": 5},
        "train_accuracy": round(train_accuracy, 4),
        "test_accuracy": round(test_accuracy, 4),
        "feature_importances": feature_importances,
        "per_class_metrics": {
            label: {
                "precision": round(float(report[label]["precision"]), 4),
                "recall": round(float(report[label]["recall"]), 4),
                "f1_score": round(float(report[label]["f1-score"]), 4),
                "support": int(report[label]["support"]),
            }
            for label in LABELS
        },
        "macro_avg": {
            "precision": round(float(report["macro avg"]["precision"]), 4),
            "recall": round(float(report["macro avg"]["recall"]), 4),
            "f1_score": round(float(report["macro avg"]["f1-score"]), 4),
        },
        "confusion_matrix": {
            "labels": LABELS,
            "matrix": matrix.tolist(),
        },
    }

    target_metrics_path = (
        Path(metrics_path) if metrics_path else DEFAULT_TOPIC_METRICS_PATH
    )
    target_metrics_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_metrics_path, "w", encoding="utf-8") as metrics_file:
        json.dump(metrics_payload, metrics_file, indent=2)

    tree_text = export_text(model, feature_names=TOPIC_FEATURE_NAMES)
    target_tree_path = Path(tree_path) if tree_path else DEFAULT_TOPIC_TREE_PATH
    target_tree_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_tree_path, "w", encoding="utf-8") as tree_file:
        tree_file.write(tree_text)

    return {
        "model": model,
        "best_params": {"criterion": "entropy", "max_depth": 5},
        "train_accuracy": train_accuracy,
        "test_accuracy": test_accuracy,
        "classification_report_str": report_text,
        "metrics": metrics_payload,
        "confusion_matrix": matrix,
        "feature_importances": feature_importances,
        "tree_text": tree_text,
        "model_path": str(target_model_path),
        "metrics_path": str(target_metrics_path),
        "tree_path": str(target_tree_path),
    }


def predict_topic_label(
    features: Any,
    model: DecisionTreeClassifier | None = None,
) -> str:
    """Predict mastery from a five-value aggregate topic feature vector."""
    if model is None:
        if not DEFAULT_TOPIC_MODEL_PATH.exists():
            model = train_topic_model(seed=42)["model"]
        else:
            model = joblib.load(DEFAULT_TOPIC_MODEL_PATH)

    if isinstance(features, dict):
        vector = [float(features.get(name, 0.0)) for name in TOPIC_FEATURE_NAMES]
    elif isinstance(features, (list, tuple, np.ndarray)):
        vector = np.asarray(features, dtype=float).reshape(-1).tolist()
    else:
        raise ValueError(f"Unsupported topic features type: {type(features)}")

    if len(vector) != len(TOPIC_FEATURE_NAMES):
        raise ValueError(
            f"Expected {len(TOPIC_FEATURE_NAMES)} topic features, got {len(vector)}"
        )
    return str(model.predict([vector])[0])


def _coerce_feature_vector(features: Any) -> np.ndarray:
    """Normalize input features into a 2D float array of shape (1, 6).

    Args:
        features: Mapping, list/tuple of floats, or ndarray.

    Returns:
        np.ndarray: 2D array of shape (1, 6).

    Raises:
        ValueError: If input structure cannot be coerced to the 6 features.
    """
    if isinstance(features, dict):
        vector = [float(features.get(col, 0.0)) for col in FEATURE_NAMES]
        return np.array([vector], dtype=float)
    if isinstance(features, (list, tuple)):
        if len(features) != len(FEATURE_NAMES):
            raise ValueError(
                f"Expected {len(FEATURE_NAMES)} features ({FEATURE_NAMES}), got {len(features)}"
            )
        return np.array([features], dtype=float)
    if isinstance(features, np.ndarray):
        arr = features.astype(float)
        if arr.ndim == 1:
            if arr.shape[0] != len(FEATURE_NAMES):
                raise ValueError(
                    f"Expected {len(FEATURE_NAMES)} features, got shape {arr.shape}"
                )
            return arr.reshape(1, -1)
        if arr.ndim == 2:
            return arr
    raise ValueError(f"Unsupported features type: {type(features)}")


def predict_label(features: Any, model: DecisionTreeClassifier | None = None) -> str:
    """Predict one of the 4 mastery labels (Weak, Good, Better, Excellent).

    Args:
        features: Feature mapping, list/tuple, or ndarray containing:
            [score_ratio, wrong_ratio, total_questions, attempt_number, previous_score_ratio, improvement]
        model: Trained DecisionTreeClassifier instance. If None, loads from DEFAULT_MODEL_PATH
            or automatically triggers training if missing.

    Returns:
        str: Predicted mastery tier ('Weak', 'Good', 'Better', 'Excellent').
    """
    if model is None:
        if not DEFAULT_MODEL_PATH.exists():
            train_result = train_model(seed=42)
            model = train_result["model"]
        else:
            model = joblib.load(DEFAULT_MODEL_PATH)

    X_input = _coerce_feature_vector(features)
    pred_label = model.predict(X_input)[0]
    return str(pred_label)


def get_feature_importances(
    model: DecisionTreeClassifier | None = None,
) -> dict[str, float]:
    """Retrieve normalized feature importances for the Decision Tree classifier.

    Args:
        model: Optional trained DecisionTreeClassifier instance. If None, loads from disk.

    Returns:
        dict[str, float]: Mapping from feature name to Gini/entropy feature importance.
    """
    if model is None:
        if not DEFAULT_MODEL_PATH.exists():
            train_result = train_model(seed=42)
            model = train_result["model"]
        else:
            model = joblib.load(DEFAULT_MODEL_PATH)

    importances = model.feature_importances_
    return {
        name: round(float(imp), 4)
        for name, imp in zip(FEATURE_NAMES, importances)
    }
