"""LLM client service supporting Google Gemini REST API and a deterministic Fake client."""

from __future__ import annotations
import base64
import json
import logging
import re
import time
from abc import ABC, abstractmethod
from typing import Any
import requests
from flask import current_app

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM client communication or configuration errors."""


class LLMRateLimitError(LLMError):
    """Exception raised when LLM service rate limit (HTTP 429) is exceeded."""


class LLMTimeoutError(LLMError):
    """Exception raised when LLM service request times out."""


def sanitize_text(text: str | None, secret_key: str | None = None) -> str:
    """Scrub sensitive API keys and query tokens from message strings.

    Args:
        text: Raw error or log message.
        secret_key: Optional API key string to replace.

    Returns:
        str: Scrubbed string safe for logging and user display.
    """
    if not text:
        return ""
    cleaned = str(text)
    if secret_key:
        cleaned = cleaned.replace(secret_key, "[REDACTED_API_KEY]")
    cleaned = re.sub(r"([?&]key=)[^&\s\"'>]+", r"\1[REDACTED_API_KEY]", cleaned)
    return cleaned


class LLMClient(ABC):
    """Abstract base class for Large Language Model clients."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        image_bytes: bytes | None = None,
        mime_type: str | None = None,
    ) -> str:
        """Send prompt and optional image bytes to LLM and return raw response text.

        Args:
            prompt: Text prompt with instructional delimiters.
            image_bytes: Optional binary content of uploaded image.
            mime_type: MIME type of the image (e.g., 'image/png').

        Returns:
            str: Raw textual response (typically JSON).

        Raises:
            LLMError: If invocation fails or returns invalid response.
        """


class GeminiClient(LLMClient):
    """Google Gemini REST API client using direct HTTP requests (no heavy SDK)."""

    DEFAULT_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int = 30,
    ) -> None:
        """Initialize Gemini client.

        Args:
            api_key: Gemini API key. Defaults to app config GEMINI_API_KEY.
            model: Model name. Defaults to app config GEMINI_MODEL or 'gemini-1.5-flash'.
            timeout: HTTP request timeout in seconds.
        """
        self.api_key = api_key or (
            current_app.config.get("GEMINI_API_KEY") if current_app else None
        )
        self.model = model or (
            current_app.config.get("GEMINI_MODEL") if current_app else None
        ) or "gemini-1.5-flash"
        self.timeout = timeout

    def _sanitize(self, msg: str) -> str:
        """Scrub this client's API key from output strings."""
        return sanitize_text(msg, self.api_key)

    def generate(
        self,
        prompt: str,
        image_bytes: bytes | None = None,
        mime_type: str | None = None,
    ) -> str:
        """Execute generateContent call against Gemini REST API with retry.

        Args:
            prompt: Text prompt instructions and study content.
            image_bytes: Optional binary image data.
            mime_type: Optional image MIME type.

        Returns:
            str: Raw JSON text returned by the model.

        Raises:
            LLMError: On API failure, bad responses, or rate limit exhaustion.
        """
        if not self.api_key:
            raise LLMError(
                "Gemini API key is not configured. Please set GEMINI_API_KEY in your environment."
            )

        parts: list[dict[str, Any]] = [{"text": prompt}]

        if image_bytes is not None:
            resolved_mime = mime_type or "image/jpeg"
            b64_data = base64.b64encode(image_bytes).decode("utf-8")
            parts.append(
                {
                    "inlineData": {
                        "mimeType": resolved_mime,
                        "data": b64_data,
                    }
                }
            )

        payload = {
            "contents": [
                {
                    "parts": parts,
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}

        last_err: Exception | None = None
        for attempt in range(2):
            try:
                resp = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if not candidates:
                            raise LLMError("Gemini API returned no candidates or content was blocked.")
                        c_parts = candidates[0].get("content", {}).get("parts", [])
                        if not c_parts or "text" not in c_parts[0]:
                            raise LLMError("Gemini API candidate contained no text content.")
                        return c_parts[0]["text"]
                    except (ValueError, KeyError, IndexError) as parse_err:
                        raise LLMError(
                            f"Failed to parse Gemini API JSON response: {self._sanitize(str(parse_err))}"
                        ) from parse_err

                # Retry on 429 or 5xx once
                if resp.status_code in {429, 500, 502, 503, 504} and attempt == 0:
                    time.sleep(1.0)
                    continue

                clean_text = self._sanitize(resp.text)
                if resp.status_code == 429:
                    raise LLMRateLimitError(
                        f"Gemini API rate limit exceeded (429): {clean_text}"
                    )
                raise LLMError(
                    f"Gemini API returned HTTP status {resp.status_code}: {clean_text}"
                )

            except (requests.Timeout, requests.ConnectionError) as net_err:
                last_err = net_err
                if attempt == 0:
                    time.sleep(1.0)
                    continue
                clean_net = self._sanitize(str(net_err))
                raise LLMTimeoutError(
                    f"Gemini API request failed due to network timeout or connection error: {clean_net}"
                ) from net_err
            except requests.RequestException as req_err:
                clean_req = self._sanitize(str(req_err))
                raise LLMError(f"Gemini API request failed: {clean_req}") from req_err

        sanitized_last = self._sanitize(str(last_err)) if last_err else "unknown error"
        raise LLMError(f"Gemini API request failed after retry: {sanitized_last}")


class FakeLLMClient(LLMClient):
    """Deterministic mock LLM client for tests and local development without API keys."""

    def __init__(self, sample_payload: dict[str, Any] | None = None) -> None:
        """Initialize FakeLLMClient.

        Args:
            sample_payload: Optional custom JSON dict to return instead of default.
        """
        self.sample_payload = sample_payload

    def generate(
        self,
        prompt: str,
        image_bytes: bytes | None = None,
        mime_type: str | None = None,
    ) -> str:
        """Return a deterministic, clearly labelled sample JSON payload.

        Args:
            prompt: Text prompt (may contain user content).
            image_bytes: Optional binary image data.
            mime_type: Optional image MIME type.

        Returns:
            str: Deterministic JSON string conforming to study schema.
        """
        if self.sample_payload is not None:
            return json.dumps(self.sample_payload)

        # Detect if custom text was passed inside delimiters
        extracted = "Extracted study text: Computer networking fundamentals, OSI model and TCP/IP protocol stack."
        if image_bytes is not None:
            extracted = "Transcribed text from uploaded image: Computer Networks, Layer Architecture, Packet Switching, and Routing Protocols."
        elif "<<<STUDY_MATERIAL_START>>>" in prompt:
            m = re.search(r"<<<STUDY_MATERIAL_START>>>(.*?)<<<STUDY_MATERIAL_END>>>", prompt, re.DOTALL)
            if m and m.group(1).strip():
                clean_snippet = m.group(1).strip()
                extracted = clean_snippet[:500]

        default_result = {
            "title": "[Sample] Computer Networking Fundamentals",
            "extracted_text": extracted,
            "summary": [
                "Computer networks enable communication and resource sharing among interconnected computing nodes.",
                "The OSI reference model defines a seven-layer architecture from physical signals to application protocols.",
                "TCP/IP is the practical four-layer protocol suite powering the modern Internet.",
                "Packet switching divides transmitted data into discrete packets routed independently across network nodes.",
                "IP addresses identify network interfaces, while port numbers direct traffic to specific host processes.",
                "DNS translates human-readable hostnames into routable numerical IP addresses."
            ],
            "simple_explanation": "Think of a computer network like a postal mail delivery system. When you send a letter, you write a clear recipient address (like an IP address) and an apartment number (like a port number). The mail carriers and sorting facilities (routers) move your letter through different checkpoints until it reaches the correct recipient without you needing to know every intermediate highway.",
            "key_terms": [
                {
                    "term": "Packet Switching",
                    "meaning": "Breaking communication into small packets routed independently across shared networks."
                },
                {
                    "term": "IP Address",
                    "meaning": "A unique numerical identifier assigned to each device connected to a computer network."
                },
                {
                    "term": "DNS",
                    "meaning": "Domain Name System: translates human-readable domain names into numerical IP addresses."
                },
                {
                    "term": "TCP",
                    "meaning": "Transmission Control Protocol: provides reliable, ordered, and error-checked byte stream delivery."
                },
                {
                    "term": "Router",
                    "meaning": "A networking device that forwards data packets between disparate computer networks."
                }
            ],
            "questions": [
                {
                    "id": 1,
                    "type": "mcq",
                    "question_text": "Which OSI layer is responsible for end-to-end communication, reliability, and flow control?",
                    "options": {
                        "A": "Physical Layer",
                        "B": "Data Link Layer",
                        "C": "Transport Layer",
                        "D": "Network Layer"
                    },
                    "correct_answer": "C",
                    "explanation": "The Transport Layer (such as TCP) manages end-to-end message delivery, flow control, and error recovery."
                },
                {
                    "id": 2,
                    "type": "mcq",
                    "question_text": "What does DNS stand for in computer networking?",
                    "options": {
                        "A": "Domain Name System",
                        "B": "Dynamic Network Service",
                        "C": "Digital Node Standard",
                        "D": "Distributed Network Switch"
                    },
                    "correct_answer": "A",
                    "explanation": "DNS stands for Domain Name System, which maps domain names to numerical IP addresses."
                },
                {
                    "id": 3,
                    "type": "mcq",
                    "question_text": "Which protocol provides connection-oriented, reliable data transmission?",
                    "options": {
                        "A": "UDP",
                        "B": "TCP",
                        "C": "ICMP",
                        "D": "IP"
                    },
                    "correct_answer": "B",
                    "explanation": "TCP establishes a virtual connection using a three-way handshake and guarantees packet delivery."
                },
                {
                    "id": 4,
                    "type": "tf",
                    "question_text": "In packet switching, all data packets must always follow the exact same physical path to their destination.",
                    "options": {
                        "True": "True",
                        "False": "False"
                    },
                    "correct_answer": "False",
                    "explanation": "Packet switching allows packets to be dynamically routed along different paths based on congestion."
                },
                {
                    "id": 5,
                    "type": "short",
                    "question_text": "What protocol translates human-readable hostnames into numerical IP addresses?",
                    "correct_answer": "DNS|Domain Name System",
                    "explanation": "DNS (Domain Name System) translates hostnames like example.com into routable IP addresses."
                },
                {
                    "id": 6,
                    "type": "theory",
                    "question_text": "Explain the difference between TCP and UDP, including their typical use cases.",
                    "correct_answer": "TCP is a connection-oriented protocol that guarantees delivery, ordering, and integrity using handshakes and acknowledgments, making it ideal for web browsing (HTTP), email, and file transfers. UDP is a connectionless, lightweight protocol that does not guarantee delivery or packet order, minimizing latency for real-time applications such as video streaming, VoIP, and multiplayer gaming.",
                    "explanation": "TCP prioritizes reliability and ordering at the expense of slight latency overhead, whereas UDP prioritizes low latency and real-time speed."
                }
            ]
        }
        return json.dumps(default_result)


def get_llm_client(
    provider: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> LLMClient:
    """Factory function returning configured LLM client instance.

    Args:
        provider: 'gemini' or 'fake'. Defaults to app config LLM_PROVIDER.
        api_key: Optional API key override.
        model: Optional model name override.

    Returns:
        LLMClient: Configured client instance.
    """
    resolved_provider = provider
    if not resolved_provider and current_app:
        resolved_provider = current_app.config.get("LLM_PROVIDER")
    resolved_provider = (resolved_provider or "gemini").lower().strip()

    if resolved_provider == "fake":
        return FakeLLMClient()
    return GeminiClient(api_key=api_key, model=model)
