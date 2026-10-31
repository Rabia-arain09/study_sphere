"""Unit tests for the markdown rendering and HTML sanitization service."""

from __future__ import annotations
from app.services.markdown_renderer import render_markdown


def test_render_markdown_empty_and_whitespace():
    """Verify that None, empty string, or whitespace returns empty string."""
    assert render_markdown(None) == ""
    assert render_markdown("") == ""
    assert render_markdown("   \n\t  ") == ""


def test_render_markdown_basic_elements():
    """Verify standard markdown headings, lists, and formatting render properly."""
    md = "# Operating Systems\n\n**Process scheduling** is *critical* for CPU efficiency.\n\n- Ready\n- Running\n- Blocked"
    html = render_markdown(md)

    assert "<h1>Operating Systems</h1>" in html or "<h1 id=" in html
    assert "<strong>Process scheduling</strong>" in html
    assert "<em>critical</em>" in html
    assert "<ul>" in html
    assert "<li>Ready</li>" in html


def test_render_markdown_code_and_tables():
    """Verify fenced code blocks and markdown tables render with syntax structures."""
    md = """| Term | Definition |
| --- | --- |
| PID | Process ID |

```python
def schedule():
    return True
```"""
    html = render_markdown(md)
    assert "<table>" in html
    assert "PID" in html
    assert "Process ID" in html
    assert "<code" in html
    assert "def schedule():" in html


def test_markdown_sanitizes_script_tags():
    """Verify script tags and malicious executable scripts are stripped."""
    malicious = "# Notes\n\n<script>alert('pwned')</script>\n<script src='https://evil.com/xss.js'></script>"
    clean = render_markdown(malicious)

    assert "<script" not in clean
    assert "alert('pwned')" not in clean
    assert "evil.com" not in clean


def test_markdown_sanitizes_event_handlers():
    """Verify inline event handlers (onerror, onload, onclick) are stripped."""
    malicious = '<img src="invalid.jpg" onerror="alert(1)"> <a href="#" onclick="steal()">Click me</a>'
    clean = render_markdown(malicious)

    assert "onerror" not in clean
    assert "onclick" not in clean
    assert "alert(1)" not in clean
    assert "steal()" not in clean


def test_markdown_sanitizes_javascript_uris():
    """Verify javascript: and data: pseudo-schemes in hyperlinks are removed."""
    malicious = "[Harmless Link](javascript:alert(document.cookie))"
    clean = render_markdown(malicious)

    assert "javascript:" not in clean
    assert "document.cookie" not in clean


def test_markdown_preserves_safe_links():
    """Verify valid HTTP/HTTPS URLs are preserved with secure link relations."""
    md = "Refer to the [Official Documentation](https://docs.python.org/3/) for details."
    html = render_markdown(md)

    assert 'href="https://docs.python.org/3/"' in html
    assert 'rel="noopener noreferrer"' in html
