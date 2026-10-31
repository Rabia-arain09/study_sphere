"""Content-based topic recommendation engine using TF-IDF and cosine similarity."""

from __future__ import annotations

import logging
from typing import Any
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class TopicRecommender:
    """Content-based curriculum topic recommender.

    Uses scikit-learn's TfidfVectorizer to construct term frequency-inverse document
    frequency feature vectors from topic titles, descriptions, metadata tags, and
    authoritative lecture note content snippets. Recommendations are determined via
    cosine similarity with an optional additive boost for topics belonging to the same
    academic subject/course.
    """

    def __init__(self, same_subject_boost: float = 0.05) -> None:
        """Initialize the topic recommender with vectorizer settings and hyperparameters.

        Args:
            same_subject_boost: Additive score boost applied to candidate topics in the
                same academic subject/course when base cosine similarity is positive.
        """
        self.same_subject_boost: float = same_subject_boost
        self._vectorizer: TfidfVectorizer = TfidfVectorizer(
            stop_words="english",
            sublinear_tf=True,
        )
        self._tfidf_matrix: Any = None
        self._sim_matrix: np.ndarray | None = None
        self._topic_ids: list[int] = []
        self._id_to_index: dict[int, int] = {}
        self._topic_subjects: dict[int, str] = {}
        self._is_fitted: bool = False

    @staticmethod
    def _extract_field(topic: Any, field_name: str, default: Any = None) -> Any:
        """Extract an attribute or dictionary item from a topic representation.

        Args:
            topic: Topic dictionary or model instance.
            field_name: Name of the property to retrieve.
            default: Fallback value if field is absent or None.

        Returns:
            Extracted field value or default.
        """
        if isinstance(topic, dict):
            val = topic.get(field_name)
            return val if val is not None else default
        val = getattr(topic, field_name, None)
        return val if val is not None else default

    def _build_topic_corpus_text(self, topic: Any) -> str:
        """Construct the aggregated text representation for a single topic.

        Repeats the topic name 3 times for elevated TF-IDF term weighting, then combines
        it with the description, serialised tags, and the first 1,500 characters of
        authoritative study notes content.

        Args:
            topic: Topic dictionary or entity.

        Returns:
            Aggregated text string for vocabulary vectorization.
        """
        name = str(self._extract_field(topic, "name", "")).strip()
        description = str(self._extract_field(topic, "description", "")).strip()
        tags_raw = self._extract_field(topic, "tags", None)
        content_raw = str(self._extract_field(topic, "content", "")).strip()

        # Format tags flexibly across list, dict, or comma/semicolon-delimited strings
        tags_text = ""
        if isinstance(tags_raw, list):
            tags_text = " ".join(str(tag) for tag in tags_raw if tag)
        elif isinstance(tags_raw, dict):
            tags_text = " ".join(f"{k} {v}" for k, v in tags_raw.items())
        elif isinstance(tags_raw, str):
            tags_text = tags_raw.replace(";", " ").replace(",", " ")

        # 3x name repetition weights topic title significantly above general body vocabulary
        weighted_name = f"{name} {name} {name}" if name else ""

        # First ~1,500 characters of lecture notes content
        content_snippet = content_raw[:1500].strip()

        text_tokens = [weighted_name, description, tags_text, content_snippet]
        return " ".join(token for token in text_tokens if token).strip()

    def fit(self, topics: list[Any]) -> TopicRecommender:
        """Fit the TF-IDF vectorizer and compute pairwise cosine similarity matrix.

        Safely handles empty topic sets, single-topic inputs, and stop-word-only documents.

        Args:
            topics: Collection of Topic entities, dictionaries, or Row objects.

        Returns:
            TopicRecommender: Self instance for method chaining.
        """
        self._topic_ids = []
        self._id_to_index = {}
        self._topic_subjects = {}
        self._tfidf_matrix = None
        self._sim_matrix = None
        self._is_fitted = False

        if not topics:
            return self

        corpus: list[str] = []
        for idx, topic in enumerate(topics):
            topic_id = int(self._extract_field(topic, "id", idx))
            subject = str(self._extract_field(topic, "subject", "")).strip()

            self._topic_ids.append(topic_id)
            self._id_to_index[topic_id] = idx
            self._topic_subjects[topic_id] = subject
            corpus.append(self._build_topic_corpus_text(topic))

        # Guard against empty corpus or all-blank text representations
        if not any(text.strip() for text in corpus):
            return self

        try:
            self._tfidf_matrix = self._vectorizer.fit_transform(corpus)
            self._sim_matrix = cosine_similarity(self._tfidf_matrix, self._tfidf_matrix)
            self._is_fitted = True
        except ValueError as err:
            # Handles scikit-learn 'empty vocabulary; perhaps documents only contain stop words'
            logger.warning("Failed to fit TfidfVectorizer on topic corpus: %s", err)
            self._is_fitted = False
            self._sim_matrix = None

        return self

    def recommend(self, topic_id: int, k: int = 5) -> list[tuple[int, float]]:
        """Recommend top-k related topics based on TF-IDF cosine similarity.

        Excludes the query topic itself and any candidates with zero cosine similarity.
        Applies a same-subject additive boost when candidate shares the query subject.

        Args:
            topic_id: Target topic ID to find recommendations for.
            k: Maximum number of recommendations to return (default: 5).

        Returns:
            list[tuple[int, float]]: List of (topic_id, score) tuples sorted by
            score descending.
        """
        if not self._is_fitted or self._sim_matrix is None or k <= 0:
            return []

        if topic_id not in self._id_to_index:
            return []

        query_idx = self._id_to_index[topic_id]
        query_subject = self._topic_subjects.get(topic_id, "")
        scores_row = self._sim_matrix[query_idx]

        candidates: list[tuple[int, float]] = []
        for candidate_idx, raw_score in enumerate(scores_row):
            # Exclude the topic itself
            if candidate_idx == query_idx:
                continue

            base_score = float(raw_score)
            # Exclude zero-score results (no vocabulary overlap)
            if base_score <= 0.0:
                continue

            candidate_id = self._topic_ids[candidate_idx]
            candidate_subject = self._topic_subjects.get(candidate_id, "")

            # Apply same-subject boost if candidate belongs to identical subject/course
            if query_subject and candidate_subject and query_subject == candidate_subject:
                final_score = min(1.0, base_score + self.same_subject_boost)
            else:
                final_score = base_score

            candidates.append((candidate_id, final_score))

        # Sort primarily by score descending, secondarily by topic_id ascending for stability
        candidates.sort(key=lambda item: (-item[1], item[0]))
        return candidates[:k]
