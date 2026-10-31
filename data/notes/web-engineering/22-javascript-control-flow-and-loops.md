---
subject: Web Engineering
topic: "JavaScript Control Flow and Loops"
semester: 5
week: "4-5"
difficulty: 1
content_source: ai_generated
content_reviewed: false
---

# JavaScript Control Flow and Loops

*Web Engineering · Semester 5 · Week 4-5 · Difficulty 1/5*

**Key concept:** Control flow decides which code runs, and loops repeat code.

## How it works
- **Decisions:** if / else if / else, switch (with break), the ternary condition ? a : b.
- **Loops:** for, while, do...while.
- **for...of** iterates over the **values** of an array. **for...in** iterates over the **keys** of an object.
- break exits a loop and continue skips to the next iteration.

## Example

Print only even numbers up to 6, then sum an array:

```javascript
for (let i = 1; i <= 6; i++) { if (i % 2 === 0) console.log(i); }  // 2 4 6
let sum = 0;
for (const n of [1, 2, 3]) sum += n;  // 6
```

## Quick check
1. What is the difference between for...of and for...in?
2. What does continue do?
