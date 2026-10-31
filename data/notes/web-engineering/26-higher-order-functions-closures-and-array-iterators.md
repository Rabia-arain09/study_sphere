---
subject: Web Engineering
topic: "Higher-Order Functions, Closures and Array Iterators"
semester: 5
week: "4-5"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Higher-Order Functions, Closures and Array Iterators

*Web Engineering · Semester 5 · Week 4-5 · Difficulty 3/5*

**Key concept:** Functions are values in JavaScript, so they can be passed around, returned and remembered, which powers closures and array methods.

## How it works
- A **higher-order function** takes or returns a function.
- A **closure** is a function that remembers the variables of the scope where it was created.
- **map** transforms each item, **filter** keeps matching items, **reduce** folds to one value, **forEach** runs a function for each item.
- map, filter and reduce return new values and do not change the original array.

## Example

Doubling, filtering and summing:

```javascript
const nums = [1, 2, 3, 4];
nums.map(n => n * 2);           // [2, 4, 6, 8]
nums.filter(n => n % 2 === 0);  // [2, 4]
nums.reduce((s, n) => s + n, 0);  // 10

function counter() { let c = 0; return () => ++c; }
const next = counter(); next(); next();  // 1, then 2
```

## Quick check
1. What does a closure remember?
2. What does reduce return?
