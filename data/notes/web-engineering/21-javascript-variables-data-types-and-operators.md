---
subject: Web Engineering
topic: "JavaScript Variables, Data Types and Operators"
semester: 5
week: "4-5"
difficulty: 1
content_source: ai_generated
content_reviewed: false
---

# JavaScript Variables, Data Types and Operators

*Web Engineering · Semester 5 · Week 4-5 · Difficulty 1/5*

**Key concept:** JavaScript stores values in variables and has a small set of data types with operators to combine them.

## How it works
- **Declare:** const (cannot be reassigned), let (block-scoped, reassignable). Avoid var.
- **Primitive types:** number, string, boolean, null, undefined, symbol, bigint. Everything else is an object.
- **Operators:** arithmetic, comparison, logical (&&, ||, !) and assignment.
- Use === (strict equality) rather than == to avoid type coercion surprises.
- typeof returns a type name. JavaScript is dynamically typed.

## Example

'5' + 3 gives '53' (string), but '5' - 3 gives 2. 5 == '5' is true, while 5 === '5' is false.

```javascript
const name = 'Ali';
let age = 20;
age = age + 1;  // 21
```

## Quick check
1. What is the result of '5' + 3?
2. What is the difference between == and ===?
