---
subject: Web Engineering
topic: "ES6 Features: Template Literals, Arrow Functions and Destructuring"
semester: 5
week: "6-8"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# ES6 Features: Template Literals, Arrow Functions and Destructuring

*Web Engineering · Semester 5 · Week 6-8 · Difficulty 2/5*

**Key concept:** ES6 added shorter, clearer syntax for strings, functions and unpacking values.

## How it works
- **Template literals** use backticks and ${expression}, and can span lines.
- **Arrow functions:** (a, b) => a + b. They have no own this, which suits callbacks.
- **Destructuring** pulls values out of arrays or objects into variables.
- **Enhanced object literals:** shorthand properties and methods, computed keys.
- Related: default parameters, rest (...args) and spread (...arr).

## Example

Combine all of these:

```javascript
const user = { name: 'Ali', age: 20 };
const { name, age } = user;
const greet = (n, a) => `${n} is ${a} years old`;
greet(name, age);  // 'Ali is 20 years old'
const [first, ...rest] = [1, 2, 3];  // 1 and [2, 3]
```

## Quick check
1. Which quote character makes a template literal?
2. What does const { name } = user do?
