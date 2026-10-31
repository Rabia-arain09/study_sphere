---
subject: Compiler Construction
topic: "Syntax-Directed Translation Basics"
semester: 5
week: "1"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Syntax-Directed Translation Basics

*Compiler Construction · Semester 5 · Week 1 · Difficulty 3/5*

**Key concept:** Syntax-directed translation attaches actions to grammar rules so the parser produces output while it parses.

## How it works
- A **translation scheme** embeds **semantic actions** inside productions.
- Actions run in the order the parse visits them.
- Infix to postfix: print the operands, then the operator.
- Postfix needs no parentheses, because the order of operators gives the meaning.

## Example

Scheme: expr -> expr + term { print('+') }, expr -> expr - term { print('-') }, term -> 0 ... 9 { print(digit) }. Input 9-5+2 prints 95-2+.

## Quick check
1. What is the postfix form of 9-5+2?
2. When does a semantic action in a translation scheme run?
