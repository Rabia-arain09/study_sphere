---
subject: Compiler Construction
topic: "Type Checking"
semester: 5
week: "6"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Type Checking

*Compiler Construction · Semester 5 · Week 6 · Difficulty 4/5*

**Key concept:** Type checking makes sure each operation is applied to compatible operands, and it inserts conversions where the language allows them.

## How it works
- A **type system** assigns a type expression to each construct, such as int or array(10, int).
- **Type synthesis** builds a type from sub-expression types. **Type inference** works out a type from how a name is used.
- **Coercion** is an implicit conversion. **Casting** is an explicit one.
- Widening (int to float) is safe. Narrowing may lose information.
- Checking can be static (compile time) or dynamic (run time).

## Example

Rule for E -> E1 + E2: if both are int the result is int. If one is float, the result is float and the int operand is converted. With int a, the expression a + 2.5 becomes inttofloat(a) + 2.5 and has type float.

## Quick check
1. What is the difference between coercion and casting?
2. What is the type of a + 2.5 if a is int?
