---
subject: Compiler Construction
topic: "Error Recovery in LR Parsing and Building a Parser"
semester: 5
week: "5"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Error Recovery in LR Parsing and Building a Parser

*Compiler Construction · Semester 5 · Week 5 · Difficulty 4/5*

**Key concept:** An LR parser detects an error as soon as no valid action exists, and it can recover by skipping input to a synchronizing point.

## How it works
- LR parsers have the **viable-prefix property**: errors are detected when the prefix read so far cannot be extended to a valid string.
- **Panic-mode recovery:** pop states until one has a goto on a chosen error non-terminal, then discard input until a token that can follow it.
- In Yacc/Bison, the special **error** token marks recovery points.
- A full parser combines the lexer, the parsing table and the semantic actions.

## Example

This rule makes the parser skip to the next semicolon after a bad statement and keep going.

```text
stmt : expr ';'
     | error ';'  { yyerrok; }
     ;
```

## Quick check
1. What is the viable-prefix property?
2. What does the error token do in Bison?
