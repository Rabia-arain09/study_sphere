---
subject: Web Engineering
topic: "Web Request-Response Cycle"
semester: 5
week: "1"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Web Request-Response Cycle

*Web Engineering · Semester 5 · Week 1 · Difficulty 2/5*

**Key concept:** The request-response cycle is everything that happens between typing a URL and seeing the page.

## How it works
- 1. The browser checks its cache, then does a **DNS lookup**.
- 2. It opens a TCP connection (and TLS for HTTPS) to the server's IP.
- 3. It sends an **HTTP request**.
- 4. The server processes it and sends an **HTTP response** (usually HTML).
- 5. The browser **renders** the page and fetches linked CSS, JavaScript and images with more requests.

## Example

One page with 1 HTML file, 2 CSS files, 3 scripts and 10 images needs 16 requests in total.

## Quick check
1. What happens first when you type a URL?
2. Why does one page often need many requests?
