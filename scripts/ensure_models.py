"""Build-time creation of missing StudySphere Decision Tree model artifacts."""

from __future__ import annotations

import logging

from ml.label_model import (
    DEFAULT_MODEL_PATH,
    DEFAULT_TOPIC_MODEL_PATH,
    train_model,
    train_topic_model,
)

logger = logging.getLogger(__name__)


def ensure_models() -> None:
    """Train and persist either Decision Tree artifact if it is missing."""
    if not DEFAULT_MODEL_PATH.is_file():
        logger.info("Training missing mastery model at %s", DEFAULT_MODEL_PATH)
        train_model(seed=42, model_path=DEFAULT_MODEL_PATH)
    if not DEFAULT_TOPIC_MODEL_PATH.is_file():
        logger.info(
            "Training missing topic mastery model at %s", DEFAULT_TOPIC_MODEL_PATH
        )
        train_topic_model(seed=42, model_path=DEFAULT_TOPIC_MODEL_PATH)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ensure_models()
