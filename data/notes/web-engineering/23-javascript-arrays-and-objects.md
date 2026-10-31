---
subject: Web Engineering
topic: "JavaScript Arrays and Objects"
semester: 5
week: "4-5"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# JavaScript Arrays and Objects

*Web Engineering · Semester 5 · Week 4-5 · Difficulty 2/5*

**Key concept:** Arrays hold ordered lists and objects hold named properties.

## How it works
- **Arrays:** zero-indexed, with length, push, pop, shift, unshift, slice, splice, indexOf, includes.
- **Objects:** key-value pairs. Access with dot (obj.name) or brackets (obj['name']).
- A function stored in an object is a **method**.
- Arrays and objects are **reference types**, so copying a variable copies the reference.

## Example

Two variables pointing to one array: a = [1, 2]; b = a; b.push(3) makes a equal to [1, 2, 3] too.

```javascript
const student = { name: 'Sara', marks: [80, 90],
  avg() { return (this.marks[0] + this.marks[1]) / 2; } };
student.avg();  // 85
```

## Quick check
1. What does push return and do?
2. Why does changing b also change a in the example?
