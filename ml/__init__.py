"""Machine learning package for StudySphere.

Contains:
- Decision Tree mastery classifier (Weak / Good / Better / Excellent)
- TF-IDF content-based topic recommender (TopicRecommender)
- Feature engineering and pipeline utilities
- Serialization / deserialization with joblib
"""

from ml.recommender import TopicRecommender
from ml.label_model import (
    predict_label,
    train_model,
    generate_synthetic_dataset,
    get_feature_importances,
    FEATURE_NAMES,
    LABELS,
)

__all__ = [
    "TopicRecommender",
    "predict_label",
    "train_model",
    "generate_synthetic_dataset",
    "get_feature_importances",
    "FEATURE_NAMES",
    "LABELS",
]
