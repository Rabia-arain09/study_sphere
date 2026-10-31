---
subject: Web Engineering
topic: "The HyperText Transfer Protocol (HTTP)"
semester: 5
week: "1"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# The HyperText Transfer Protocol (HTTP)

*Web Engineering · Semester 5 · Week 1 · Difficulty 2/5*

**Key concept:** HTTP is the request-response protocol the Web uses. The client sends a request and the server returns a response.

## How it works
- A request has a **method**, path, headers and an optional body.
- **Methods:** GET (read), POST (create), PUT (replace), PATCH (update part), DELETE (remove).
- A response has a **status code**, headers and a body.
- **Status codes:** 2xx success, 3xx redirect, 4xx client error, 5xx server error.
- HTTP is **stateless**: each request is independent. **HTTPS** adds encryption (TLS).

## Example

A browser asks for a page that does not exist and the server answers 404 Not Found.

```http
GET /about.html HTTP/1.1
Host: www.example.com

HTTP/1.1 404 Not Found
```

## Quick check
1. What does the status code 500 mean?
2. Why is HTTP called stateless?
