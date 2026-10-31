---
subject: Web Engineering
topic: "Local Storage and Cookies"
semester: 5
week: "4-5"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Local Storage and Cookies

*Web Engineering · Semester 5 · Week 4-5 · Difficulty 2/5*

**Key concept:** Browsers can save small amounts of data on the user's device with Local Storage, session storage and cookies.

## How it works
- **localStorage:** key-value strings, stays until cleared, about 5 MB, never sent to the server.
- **sessionStorage:** same API but cleared when the tab closes.
- **Cookies:** small (about 4 KB), sent with **every** HTTP request, can have an expiry. Used for sessions and login.
- Store objects with JSON.stringify and read with JSON.parse.
- Never store passwords or other secrets in browser storage.

## Example

Save and read a theme preference:

```javascript
localStorage.setItem('theme', 'dark');
localStorage.getItem('theme');  // 'dark'
```

## Quick check
1. Which is sent to the server on every request, cookies or localStorage?
2. How do you store an object in localStorage?
