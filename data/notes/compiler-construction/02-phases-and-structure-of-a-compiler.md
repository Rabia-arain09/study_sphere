---
subject: Compiler Construction
topic: "Phases and Structure of a Compiler"
semester: 5
week: "1"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Phases and Structure of a Compiler

*Compiler Construction · Semester 5 · Week 1 · Difficulty 2/5*

**Key concept:** A compiler works in phases, each turning one representation of the program into the next.

## How it works
- **Front end (analysis):** lexical analysis, syntax analysis, semantic analysis, intermediate-code generation.
- **Back end (synthesis):** code optimization and code generation.
- The **symbol table** and **error handler** are used by every phase.
- The front end depends on the source language and the back end on the target machine, so parts can be reused.

## Example

For position = initial + rate * 60: the lexer gives id1 = id2 + id3 * 60. Semantic analysis inserts a conversion of 60 to float. The intermediate code is:

```text
t1 = inttofloat(60)
t2 = id3 * t1
t3 = id2 + t2
id1 = t3
```

## Quick check
1. Which phases form the front end?
2. Why do all phases use the symbol table?
