"""Tests for LLM Speed, Timeout, Parallel Generation, Error Sanitization, and llm-check CLI."""

from __future__ import annotations
import json
import logging
from unittest.mock import MagicMock, patch
import pytest
import requests
from flask import Flask
from app.extensions import db
from app.models.upload import Upload
from app.models.user import User
from app.services.llm_client import (
    FakeLLMClient,
    GeminiClient,
    LLMClient,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    normalize_timeout,
    sanitize_text,
)
from app.services.upload_service import (
    DailyLimitExceededError,
    LLMGenerationError,
    generate_study_artifacts,
    process_text_upload,
    validate_and_repair_quiz,
    validate_and_repair_study_guide,
)


# ==============================================================================
# 1. Timeout Configuration & Client Initialization
# ==============================================================================


def test_gemini_client_reads_timeouts_from_config(app: Flask) -> None:
    """Verify GeminiClient reads default and configured GEMINI_TIMEOUT from app config."""
    with app.app_context():
        # Custom tuple configuration
        app.config["GEMINI_TIMEOUT"] = (5, 45)
        client = GeminiClient()
        assert client.timeout == (5, 45)
        assert normalize_timeout(client.timeout) == (5.0, 45.0)

        # Single integer configuration
        app.config["GEMINI_TIMEOUT"] = 60
        client2 = GeminiClient()
        assert normalize_timeout(client2.timeout) == (10.0, 60.0)

        # Explicit constructor override takes precedence
        client3 = GeminiClient(timeout=(8, 90))
        assert normalize_timeout(client3.timeout) == (8.0, 90.0)


def test_normalize_timeout_helper() -> None:
    """Verify normalize_timeout handles tuples, numbers, and fallbacks."""
    assert normalize_timeout((15, 90)) == (15.0, 90.0)
    assert normalize_timeout([20, 150]) == (20.0, 150.0)
    assert normalize_timeout(45) == (10.0, 45.0)
    assert normalize_timeout(None) == (10.0, 120.0)


# ==============================================================================
# 2. No Retry on Read Timeout; Retry on 429 and 5xx
# ==============================================================================


def test_no_retry_after_read_timeout() -> None:
    """Verify ReadTimeout raises LLMTimeoutError immediately with NO retry."""
    with patch("requests.post") as mock_post:
        mock_post.side_effect = requests.exceptions.ReadTimeout("The read operation timed out")
        client = GeminiClient(api_key="test-api-key")

        with pytest.raises(LLMTimeoutError, match="timed out"):
            client.generate("Test prompt")

        # Must not retry after read timeout (exactly 1 call)
        assert mock_post.call_count == 1


def test_retry_once_on_429() -> None:
    """Verify GeminiClient retries once with backoff on HTTP 429 and succeeds on 2nd attempt."""
    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    mock_resp_429.text = "Resource has been exhausted (e.g. check quota)."

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": '{"result": "ok"}'}]}}]
    }

    with patch("requests.post") as mock_post, patch("time.sleep") as mock_sleep:
        mock_post.side_effect = [mock_resp_429, mock_resp_200]
        client = GeminiClient(api_key="test-api-key")

        result = client.generate("Test prompt")
        assert result == '{"result": "ok"}'
        assert mock_post.call_count == 2
        mock_sleep.assert_called_once_with(1.0)


def test_retry_exhausted_on_persistent_429() -> None:
    """Verify GeminiClient raises LLMRateLimitError when 429 persists across retry."""
    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    mock_resp_429.text = "Quota exceeded."

    with patch("requests.post") as mock_post, patch("time.sleep"):
        mock_post.return_value = mock_resp_429
        client = GeminiClient(api_key="test-api-key")

        with pytest.raises(LLMRateLimitError, match="rate limit exceeded"):
            client.generate("Test prompt")

        assert mock_post.call_count == 2


# ==============================================================================
# 3. 400 on generationConfig Triggers Single Retry Without Field
# ==============================================================================


def test_400_on_generation_config_retries_without_field() -> None:
    """Verify 400 on generationConfig drops the offending field, retries, and remembers it."""
    GeminiClient.reset_unsupported_fields()

    mock_resp_400 = MagicMock()
    mock_resp_400.status_code = 400
    mock_resp_400.text = 'Invalid JSON payload received. Unknown name "thinkingConfig" at generationConfig'

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": '{"status": "success"}'}]}}]
    }

    with patch("requests.post") as mock_post:
        mock_post.side_effect = [mock_resp_400, mock_resp_200]
        client = GeminiClient(api_key="test-api-key")

        res = client.generate("Test prompt")
        assert res == '{"status": "success"}'
        assert mock_post.call_count == 2

        # 1st call included thinkingConfig
        call_1_cfg = mock_post.call_args_list[0][1]["json"]["generationConfig"]
        assert "thinkingConfig" in call_1_cfg

        # 2nd call dropped thinkingConfig
        call_2_cfg = mock_post.call_args_list[1][1]["json"]["generationConfig"]
        assert "thinkingConfig" not in call_2_cfg

        # Verify thinkingConfig is remembered as unsupported for subsequent calls
        assert "thinkingConfig" in GeminiClient._unsupported_fields

        # A 2nd generation immediately omits thinkingConfig without error
        mock_post.side_effect = [mock_resp_200]
        client.generate("Second prompt")
        call_3_cfg = mock_post.call_args_list[2][1]["json"]["generationConfig"]
        assert "thinkingConfig" not in call_3_cfg


def test_400_on_response_schema_retries_without_field() -> None:
    """Verify 400 citing responseSchema drops the schema and retries once."""
    GeminiClient.reset_unsupported_fields()

    mock_resp_400 = MagicMock()
    mock_resp_400.status_code = 400
    mock_resp_400.text = 'Invalid JSON payload. Field responseSchema is not supported for this model.'

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": '{"result": "recovered"}'}]}}]
    }

    with patch("requests.post") as mock_post:
        mock_post.side_effect = [mock_resp_400, mock_resp_200]
        client = GeminiClient(api_key="test-api-key")

        res = client.generate("Test prompt", response_schema={"type": "OBJECT"})
        assert res == '{"result": "recovered"}'
        assert mock_post.call_count == 2

        call_2_cfg = mock_post.call_args_list[1][1]["json"]["generationConfig"]
        assert "responseSchema" not in call_2_cfg
        assert "responseSchema" in GeminiClient._unsupported_fields


def test_response_schema_omits_incompatible_thinking_config() -> None:
    """Keep Gemini structured output enabled without its incompatible thinking config."""
    GeminiClient.reset_unsupported_fields()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": '{"answer": "ok"}'}]}}]
    }
    response_schema = {
        "type": "OBJECT",
        "properties": {"answer": {"type": "STRING"}},
        "required": ["answer"],
    }

    with patch("requests.post", return_value=mock_resp) as mock_post:
        client = GeminiClient(api_key="test-api-key")

        result = client.generate(
            "Return a short answer.",
            response_schema=response_schema,
        )

    assert result == '{"answer": "ok"}'
    assert mock_post.call_count == 1
    generation_config = mock_post.call_args.kwargs["json"]["generationConfig"]
    assert generation_config["responseSchema"] == response_schema
    assert "thinkingConfig" not in generation_config


# ==============================================================================
# 4. Parallel Generation & Two Parts Merged Correctly
# ==============================================================================


def test_two_parts_merged_correctly() -> None:
    """Verify study guide and quiz parts are generated concurrently and merged correctly."""
    result = generate_study_artifacts(
        "Introduction to Operating Systems: processes, threads, virtual memory, and concurrency.",
        client=FakeLLMClient(),
    )

    # Check study guide fields
    assert "title" in result and len(result["title"]) > 0
    assert "summary" in result and 5 <= len(result["summary"]) <= 8
    assert "simple_explanation" in result and len(result["simple_explanation"]) > 0
    assert "key_terms" in result and 1 <= len(result["key_terms"]) <= 10

    # Check quiz fields
    questions = result["questions"]
    assert len(questions) == 6
    mcqs = [q for q in questions if q["type"] == "mcq"]
    tfs = [q for q in questions if q["type"] == "tf"]
    shorts = [q for q in questions if q["type"] == "short"]
    theories = [q for q in questions if q["type"] == "theory"]

    assert len(mcqs) == 3
    assert len(tfs) == 1
    assert len(shorts) == 1
    assert len(theories) == 1


def test_one_failing_part_fails_whole_upload_and_saves_nothing(
    app: Flask, test_user: User
) -> None:
    """Ensure failure in either guide or quiz causes whole upload to fail and save nothing."""
    mock_client = MagicMock()

    # Define side effect where guide succeeds but quiz returns invalid JSON
    def failing_generate(prompt: str, **kwargs):
        if "assessment quiz" in prompt:
            return "Invalid non-JSON quiz output"
        return json.dumps(
            {
                "title": "OS Memory Management",
                "summary": [f"Point {i}" for i in range(5)],
                "simple_explanation": "Memory management allocates physical RAM efficiently.",
                "key_terms": [{"term": "Paging", "meaning": "Fixed-size memory allocation"}],
            }
        )

    mock_client.generate.side_effect = failing_generate

    with app.app_context():
        initial_count = Upload.query.count()

        with pytest.raises(LLMGenerationError, match="Failed to generate valid quiz"):
            process_text_upload(
                user_id=test_user.id,
                raw_text="Operating systems memory management and paging mechanisms.",
                llm_client=mock_client,
            )

        # Nothing must be saved in the database
        assert Upload.query.count() == initial_count


def test_failed_generation_does_not_consume_daily_quota(
    app: Flask, test_user: User
) -> None:
    """Ensure a failed generation does NOT count toward the user's UPLOAD_DAILY_LIMIT."""
    with app.app_context():
        app.config["UPLOAD_DAILY_LIMIT"] = 2

        # 1. Trigger failed generation
        failing_client = MagicMock()
        failing_client.generate.return_value = "Broken output forever"

        with pytest.raises(LLMGenerationError):
            process_text_upload(
                user_id=test_user.id,
                raw_text="Failing material content attempt.",
                llm_client=failing_client,
            )

        # Upload count in database remains 0
        assert Upload.query.filter_by(user_id=test_user.id).count() == 0

        # 2. User can still execute their full quota of 2 successful uploads
        u1, is_new1 = process_text_upload(
            user_id=test_user.id,
            raw_text="First successful study text for quota test.",
            llm_client=FakeLLMClient(),
        )
        assert is_new1 is True

        u2, is_new2 = process_text_upload(
            user_id=test_user.id,
            raw_text="Second successful study text for quota test.",
            llm_client=FakeLLMClient(),
        )
        assert is_new2 is True

        # 3. Third generation now exceeds quota as expected
        with pytest.raises(DailyLimitExceededError, match="reached your daily generation limit"):
            process_text_upload(
                user_id=test_user.id,
                raw_text="Third study text should exceed daily limit.",
                llm_client=FakeLLMClient(),
            )


# ==============================================================================
# 5. Security: API Key Never Exposed in Errors or Logs
# ==============================================================================


def test_api_key_never_appears_in_error_messages_or_logs(caplog: pytest.LogCaptureFixture) -> None:
    """Verify API keys are completely scrubbed from error messages, exceptions, and logs."""
    secret_key = "AIzaSySecretApiKey1234567890abcdef"
    client = GeminiClient(api_key=secret_key)

    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.text = f"Forbidden: API key {secret_key} is invalid for endpoint ?key={secret_key}"

    with patch("requests.post", return_value=mock_resp):
        with pytest.raises(LLMError) as exc_info:
            client.generate("Test prompt")

        err_str = str(exc_info.value)
        assert secret_key not in err_str
        assert "[REDACTED_API_KEY]" in err_str

    # Test sanitize_text utility directly
    leaked = f"https://api.google.com/test?key={secret_key}&other=123 with key {secret_key}"
    cleaned = sanitize_text(leaked, secret_key)
    assert secret_key not in cleaned
    assert "[REDACTED_API_KEY]" in cleaned


# ==============================================================================
# 6. Input Text Capping to 12,000 Characters for LLM
# ==============================================================================


def test_input_cap_of_12000_characters(app: Flask, test_user: User) -> None:
    """Verify input text sent to LLM prompt is capped at 12000 chars while full text is stored."""
    # Create 15,000-character text input
    base_sentence = "Computer networks coordinate message delivery across packet switched routers. "
    repetitions = (15000 // len(base_sentence)) + 2
    full_text = (base_sentence * repetitions)[:15000]
    assert len(full_text) == 15000

    prompts_captured: list[str] = []

    class CapturingClient(LLMClient):
        def generate(self, prompt: str, **kwargs) -> str:
            prompts_captured.append(prompt)
            if "assessment quiz" in prompt:
                return json.dumps(
                    {
                        "questions": [
                            {
                                "type": "mcq",
                                "question_text": "Q1",
                                "options": {"A": "1", "B": "2", "C": "3", "D": "4"},
                                "correct_answer": "A",
                                "explanation": "E",
                            },
                            {
                                "type": "mcq",
                                "question_text": "Q2",
                                "options": {"A": "1", "B": "2", "C": "3", "D": "4"},
                                "correct_answer": "B",
                                "explanation": "E",
                            },
                            {
                                "type": "mcq",
                                "question_text": "Q3",
                                "options": {"A": "1", "B": "2", "C": "3", "D": "4"},
                                "correct_answer": "C",
                                "explanation": "E",
                            },
                            {
                                "type": "tf",
                                "question_text": "Q4",
                                "options": {"True": "True", "False": "False"},
                                "correct_answer": "True",
                                "explanation": "E",
                            },
                            {
                                "type": "short",
                                "question_text": "Q5",
                                "correct_answer": "Ans",
                                "explanation": "E",
                            },
                            {
                                "type": "theory",
                                "question_text": "Q6",
                                "correct_answer": "Model Ans",
                                "explanation": "E",
                            },
                        ]
                    }
                )
            return json.dumps(
                {
                    "title": "Computer Networks Overview",
                    "summary": [f"Core concept bullet {i}" for i in range(5)],
                    "simple_explanation": "Networks allow computers to exchange packets.",
                    "key_terms": [{"term": "Router", "meaning": "Packet forwarder"}],
                }
            )

    capturing_client = CapturingClient()

    with app.app_context():
        upload, is_new = process_text_upload(
            user_id=test_user.id,
            raw_text=full_text,
            llm_client=capturing_client,
        )

        assert is_new is True
        # Full 15,000 chars stored in database
        assert len(upload.extracted_text) == 15000

        # LLM prompts must not contain more than 12000 characters of the study material
        assert len(prompts_captured) >= 2
        for prompt in prompts_captured:
            # Extract content between delimiters
            start_delim = "<<<STUDY_MATERIAL_START>>>\n"
            end_delim = "\n<<<STUDY_MATERIAL_END>>>"
            start_idx = prompt.find(start_delim)
            end_idx = prompt.find(end_delim)
            assert start_idx != -1 and end_idx != -1
            embedded_material = prompt[start_idx + len(start_delim) : end_idx]
            assert len(embedded_material) <= 12000


# ==============================================================================
# 7. CLI Command llm-check
# ==============================================================================


def test_llm_check_cli_command_fake_provider(app: Flask) -> None:
    """Verify llm-check CLI command works cleanly when LLM_PROVIDER=fake."""
    runner = app.test_cli_runner()

    with app.app_context():
        app.config["LLM_PROVIDER"] = "fake"
        result = runner.invoke(args=["llm-check"])

        assert result.exit_code == 0
        assert "Provider: fake" in result.output
        assert "gemini-3.5-flash-lite" in result.output
        assert "fake provider, no network call" in result.output


def test_llm_check_cli_command_gemini_success(app: Flask) -> None:
    """Verify llm-check CLI command outputs HTTP status 200 and seconds taken."""
    runner = app.test_cli_runner()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "Hello there student!"}]}}]
    }

    with app.app_context():
        app.config["LLM_PROVIDER"] = "gemini"
        app.config["GEMINI_API_KEY"] = "secret-gemini-key-999"

        with patch("requests.post", return_value=mock_resp):
            result = runner.invoke(args=["llm-check"])

            assert result.exit_code == 0
            assert "Provider: gemini" in result.output
            assert "HTTP status: 200" in result.output
            assert "Time:" in result.output
            assert "secret-gemini-key-999" not in result.output


def test_llm_check_cli_command_gemini_error(app: Flask) -> None:
    """Verify llm-check CLI command handles errors cleanly without exposing secret key."""
    runner = app.test_cli_runner()

    secret = "my-confidential-api-key"
    with app.app_context():
        app.config["LLM_PROVIDER"] = "gemini"
        app.config["GEMINI_API_KEY"] = secret

        with patch("requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.ReadTimeout(
                f"Timeout requesting https://api.google.com?key={secret}"
            )
            result = runner.invoke(args=["llm-check"])

            assert result.exit_code == 0
            assert "Provider: gemini" in result.output
            assert "Error type: LLMTimeoutError" in result.output
            assert "Time:" in result.output
            # Secret key must NEVER appear in output
            assert secret not in result.output
            assert "[REDACTED_API_KEY]" in result.output
