---
subject: Web Engineering
topic: "JavaScript Functions and Scope"
semester: 5
week: "4-5"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# JavaScript Functions and Scope

*Web Engineering · Semester 5 · Week 4-5 · Difficulty 2/5*

**Key concept:** Functions package reusable code, and scope decides where a variable can be seen.

## How it works
- **Declaration:** function add(a, b) { return a + b; } is hoisted, so it can be called before it appears.
- **Function expressions** and **arrow functions** (a, b) => a + b are values assigned to variables.
- **Anonymous** functions have no name and are often passed as callbacks.
- **Scope:** global, function and block (let and const). Inner scopes can read outer variables.
- Default parameters: function f(x = 1).

## Example

A variable declared with let inside an if block is not visible outside it.

```javascript
const square = n => n * n;
square(4);  // 16
if (true) { let x = 1; }
console.log(x);  // ReferenceError
```

## Quick check
1. What does hoisting mean for function declarations?
2. Which variables are block scoped?
