---
subject: Web Engineering
topic: "Web Application Architecture"
semester: 5
week: "1"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Web Application Architecture

*Web Engineering · Semester 5 · Week 1 · Difficulty 3/5*

**Key concept:** Architecture divides a web application into tiers so each part can change and scale independently.

## How it works
- **Single tier:** presentation, logic and data all in one place.
- **Two tier (client-server):** the client holds the UI and logic, the server holds the database.
- **Three tier:** a **presentation** tier (browser), a **logic** tier (application server) and a **data** tier (database).
- Three-tier is the standard: easier to maintain, scale and secure.

## Example

In an online shop the browser shows products (presentation), a Node server applies pricing rules (logic), and MySQL stores orders (data). The browser never talks to the database directly.

## Quick check
1. Name the three tiers.
2. Why is a three-tier design easier to scale than a single tier?
