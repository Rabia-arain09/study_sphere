---
subject: Compiler Construction
topic: "FIRST and FOLLOW Sets"
semester: 5
week: "3"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# FIRST and FOLLOW Sets

*Compiler Construction · Semester 5 · Week 3 · Difficulty 4/5*

**Key concept:** FIRST and FOLLOW tell a predictive parser which production to choose.

## How it works
- **FIRST(alpha):** the terminals that can begin a string derived from alpha. It includes epsilon if alpha can derive the empty string.
- **FOLLOW(A):** the terminals that can appear right after A in some derivation. FOLLOW of the start symbol contains $.
- To compute FOLLOW: for B -> alpha A beta add FIRST(beta) minus epsilon. If beta can vanish, add FOLLOW(B).
- Repeat until no set changes.

## Example

Grammar: E -> T E', E' -> + T E' | e, T -> F T', T' -> * F T' | e, F -> ( E ) | id. FIRST(E) = FIRST(T) = FIRST(F) = { (, id }. FIRST(E') = { +, e }. FIRST(T') = { *, e }. FOLLOW(E) = FOLLOW(E') = { ), $ }. FOLLOW(T) = FOLLOW(T') = { +, ), $ }. FOLLOW(F) = { *, +, ), $ }.

## Quick check
1. Why does FOLLOW(E) contain $?
2. When is epsilon in FIRST of a symbol?
