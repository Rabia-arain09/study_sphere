---
subject: Web Engineering
topic: "Introduction to Node.js"
semester: 5
week: "11-13"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Introduction to Node.js

*Web Engineering · Semester 5 · Week 11-13 · Difficulty 2/5*

**Key concept:** Node.js runs JavaScript outside the browser, using a non-blocking, event-driven model.

## How it works
- Node uses Google's **V8** engine and lets you write server code in JavaScript.
- **Traditional servers** often start a thread per request. **Node** uses one thread with an **event loop**.
- **Non-blocking I/O:** slow operations (files, network, database) are started and a callback runs when they finish.
- It is great for many concurrent I/O tasks and weak for heavy CPU work.

## Example

Reading a file does not freeze the server: Node starts the read, serves other requests, and runs the callback when the data is ready.

```javascript
const fs = require('fs');
fs.readFile('a.txt', 'utf8', (err, data) => console.log(data));
console.log('This prints first');
```

## Quick check
1. What is the event loop?
2. Why is Node weak for CPU-heavy work?
