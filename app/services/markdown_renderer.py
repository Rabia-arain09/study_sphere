"""Markdown rendering and HTML sanitization service for StudySphere study notes."""

from __future__ import annotations
import functools
import hashlib
import math
import markdown
import nh3

# Allowlist of safe HTML tags suitable for technical notes, formulas, code, and tables
ALLOWED_TAGS: set[str] = {
    "a",
    "abbr",
    "b",
    "blockquote",
    "br",
    "code",
    "dd",
    "del",
    "details",
    "div",
    "dl",
    "dt",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "img",
    "ins",
    "kbd",
    "li",
    "mark",
    "ol",
    "p",
    "pre",
    "q",
    "s",
    "samp",
    "small",
    "span",
    "strong",
    "sub",
    "summary",
    "sup",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "u",
    "ul",
    "var",
}

# Allowlist of tag attributes ensuring links and code formatting remain intact while stripping XSS vectors
ALLOWED_ATTRIBUTES: dict[str, set[str]] = {
    "*": {"class", "id", "title"},
    "a": {"href", "title", "target"},
    "img": {"src", "alt", "title", "width", "height"},
    "th": {"scope", "colspan", "rowspan", "align"},
    "td": {"colspan", "rowspan", "align"},
}

_CONTENT_CACHE_STORE: dict[str, str] = {}


def render_markdown(content: str | None) -> str:
    """Render Markdown string to sanitized HTML.

    AI-generated and student-facing lecture notes are converted to semantic HTML
    via python-markdown and sanitized via nh3 (Ammonia Rust library) to eliminate
    script execution, malicious event handlers, and unsafe URL protocols.

    Args:
        content: Raw markdown text or None.

    Returns:
        str: Sanitized HTML string safe for Jinja template rendering via |safe.
    """
    if not content or not content.strip():
        return ""

    raw_html = markdown.markdown(
        content.strip(),
        extensions=[
            "extra",
            "fenced_code",
            "tables",
            "toc",
            "sane_lists",
            "nl2br",
        ],
        output_format="html5",
    )

    sanitized_html = nh3.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes={"http", "https", "mailto"},
    )

    return sanitized_html


@functools.lru_cache(maxsize=1024)
def get_cached_topic_markdown(topic_id: int, content_hash: str) -> str:
    """Retrieve or compute rendered markdown HTML keyed strictly by topic ID and content hash.

    Args:
        topic_id: Primary key of the topic.
        content_hash: SHA-256 hash digest of the raw markdown text.

    Returns:
        str: Sanitized HTML rendered from the stored content matching the content hash.
    """
    raw_content = _CONTENT_CACHE_STORE.get(content_hash, "")
    return render_markdown(raw_content)


def render_topic_markdown(topic_id: int, content: str | None) -> str:
    """Render topic Markdown notes to HTML with in-memory LRU caching.

    Uses SHA-256 content hashing to derive a cache key (topic_id, content_hash)
    for functools.lru_cache, avoiding expensive repeated markdown parsing and
    HTML sanitization on subsequent page views.

    Args:
        topic_id: Primary key of the topic.
        content: Raw markdown content string or None.

    Returns:
        str: Sanitized HTML string ready for template rendering.
    """
    if not content or not content.strip():
        return ""

    content_hash = hashlib.sha256(content.strip().encode("utf-8")).hexdigest()
    _CONTENT_CACHE_STORE[content_hash] = content
    return get_cached_topic_markdown(topic_id, content_hash)


def clear_topic_markdown_cache() -> None:
    """Clear in-memory LRU cache and underlying content store."""
    get_cached_topic_markdown.cache_clear()
    _CONTENT_CACHE_STORE.clear()


def calculate_reading_time(content: str | None) -> str | None:
    """Calculate estimated reading time from content word count.

    Computes reading time assuming an average reading speed of approximately
    200 words per minute, enforcing a minimum of 1 minute for non-empty content.
    Returns None if content is empty or contains no words.

    Args:
        content: Raw text or Markdown content string.

    Returns:
        str | None: Formatted reading time string (e.g., '6 min read') or None.
    """
    if hasattr(content, "content"):
        content = getattr(content, "content")

    if not content or not isinstance(content, str) or not content.strip():
        return None

    words = len(content.split())
    if words == 0:
        return None

    minutes = max(1, math.ceil(words / 200))
    return f"{minutes} min read"


