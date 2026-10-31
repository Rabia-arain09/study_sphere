---
subject: Web Engineering
topic: "JavaScript Errors and Exception Handling"
semester: 5
week: "4-5"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# JavaScript Errors and Exception Handling

*Web Engineering · Semester 5 · Week 4-5 · Difficulty 2/5*

**Key concept:** Exception handling lets a program catch runtime errors and keep running instead of crashing.

## How it works
- **Error types:** SyntaxError, ReferenceError, TypeError, RangeError.
- **try** holds code that may fail, **catch (e)** handles the error, **finally** always runs.
- **throw** raises your own error, usually new Error('message').
- Do not use try/catch to hide bugs, and always report the problem.

## Example

Parsing bad JSON throws, and the catch block handles it.

```javascript
try {
  JSON.parse('{bad');
} catch (e) {
  console.log('Invalid JSON:', e.message);
} finally {
  console.log('done');
}
```

## Quick check
1. When does the finally block run?
2. How do you raise your own error?
