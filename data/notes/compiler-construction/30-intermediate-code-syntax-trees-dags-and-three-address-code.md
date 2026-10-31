---
subject: Compiler Construction
topic: "Intermediate Code: Syntax Trees, DAGs and Three-Address Code"
semester: 5
week: "6"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Intermediate Code: Syntax Trees, DAGs and Three-Address Code

*Compiler Construction · Semester 5 · Week 6 · Difficulty 4/5*

**Key concept:** Intermediate code is a machine-independent form between the front end and the back end.

## How it works
- A **syntax tree** shows the structure of an expression. A **DAG** shares identical subexpressions.
- **Three-address code** has at most one operator per instruction: x = y op z.
- Stored as **quadruples** (op, arg1, arg2, result) or triples.
- Compound expressions need temporaries.

## Example

a = b * -c + b * -c as three-address code, and with a DAG that shares the repeated part:

```text
// tree                // DAG
t1 = minus c         t1 = minus c
t2 = b * t1          t2 = b * t1
t3 = minus c         t5 = t2 + t2
t4 = b * t3          a  = t5
t5 = t2 + t4
a  = t5
```

## Quick check
1. What is the advantage of a DAG over a syntax tree?
2. What is the form of a quadruple?
