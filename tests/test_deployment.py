"""Tests for deployment model preparation."""

from pathlib import Path

import pytest

from scripts import ensure_models


def test_ensure_models_trains_only_missing_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Train and persist both artifacts when neither has been built yet."""
    model_path = tmp_path / "label_model.joblib"
    topic_model_path = tmp_path / "topic_label_model.joblib"
    trained_paths: list[Path] = []

    def save_artifact(*, seed: int, model_path: Path) -> None:
        assert seed == 42
        model_path.parent.mkdir(parents=True, exist_ok=True)
        model_path.touch()
        trained_paths.append(model_path)

    monkeypatch.setattr(ensure_models, "DEFAULT_MODEL_PATH", model_path)
    monkeypatch.setattr(ensure_models, "DEFAULT_TOPIC_MODEL_PATH", topic_model_path)
    monkeypatch.setattr(ensure_models, "train_model", save_artifact)
    monkeypatch.setattr(ensure_models, "train_topic_model", save_artifact)

    ensure_models.ensure_models()
    ensure_models.ensure_models()

    assert trained_paths == [model_path, topic_model_path]
    assert model_path.is_file()
    assert topic_model_path.is_file()
