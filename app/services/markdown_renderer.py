"""Markdown rendering and HTML sanitization service for StudySphere study notes."""

from __future__ import annotations
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
