"""Machine learning package for StudySphere.

Contains:
- Decision Tree mastery classifier (Weak / Good / Better / Excellent)
- TF-IDF content-based topic recommender (TopicRecommender)
- Feature engineering and pipeline utilities
- Serialization / deserialization with joblib
"""

from ml.recommender import TopicRecommender

__all__ = ["TopicRecommender"]
