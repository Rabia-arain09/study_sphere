---
subject: Web Engineering
topic: "Promises and Asynchronous JavaScript"
semester: 5
week: "6-8"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Promises and Asynchronous JavaScript

*Web Engineering · Semester 5 · Week 6-8 · Difficulty 4/5*

**Key concept:** A promise stands for a value that will arrive later, so JavaScript can wait for slow work without freezing.

## How it works
- JavaScript is single-threaded. Slow tasks (network, timers) are **asynchronous**, so the page stays responsive.
- A **Promise** is **pending**, then **fulfilled** (value) or **rejected** (error).
- Chain with **.then(onSuccess)** and **.catch(onError)**.
- **async / await** is cleaner syntax: await pauses an async function until the promise settles.
- **Promise.all** waits for several promises.

## Example

Fetch data and handle failure:

```javascript
fetch('/api/users')
  .then(res => res.json())
  .then(data => console.log(data))
  .catch(err => console.error(err));
```

## Quick check
1. What are the three states of a promise?
2. What does await do?
