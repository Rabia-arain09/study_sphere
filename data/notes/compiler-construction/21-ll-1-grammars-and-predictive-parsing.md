---
subject: Compiler Construction
topic: "LL(1) Grammars and Predictive Parsing"
semester: 5
week: "3"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# LL(1) Grammars and Predictive Parsing

*Compiler Construction · Semester 5 · Week 3 · Difficulty 4/5*

**Key concept:** An LL(1) grammar lets a parser choose each production from one token of lookahead, using a table and a stack.

## How it works
- For A -> alpha | beta, FIRST(alpha) and FIRST(beta) must not overlap.
- If epsilon is in FIRST(alpha), then FIRST(beta) must not overlap FOLLOW(A).
- The **parsing table** M[A, a] holds the production to use. The parser keeps a stack of grammar symbols and the input.
- If the top is a terminal, match it. If it is a non-terminal, replace it with the production body.
- A blank cell is a syntax error.

## Example

With the expression grammar above, input id: stack $E, input id$. E -> T E', T -> F T', F -> id, match id, T' -> e, E' -> e, and $ is matched. The input is accepted.

## Quick check
1. State the LL(1) condition for A -> alpha | beta.
2. What does an empty table entry mean?
