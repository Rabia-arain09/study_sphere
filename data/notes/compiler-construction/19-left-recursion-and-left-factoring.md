---
subject: Compiler Construction
topic: "Left Recursion and Left Factoring"
semester: 5
week: "3"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Left Recursion and Left Factoring

*Compiler Construction · Semester 5 · Week 3 · Difficulty 4/5*

**Key concept:** Grammars must be rewritten to remove left recursion and common prefixes before top-down parsing.

## How it works
- Left recursion A -> A alpha | beta becomes A -> beta A' and A' -> alpha A' | epsilon.
- Left factoring A -> alpha beta1 | alpha beta2 becomes A -> alpha A' and A' -> beta1 | beta2.
- Both transformations keep the same language.
- Left factoring lets the parser delay the choice until it has seen more input.

## Example

E -> E + T | T becomes E -> T E' and E' -> + T E' | epsilon. S -> iEtS | iEtSeS | a becomes S -> iEtS S' | a and S' -> eS | epsilon.

## Quick check
1. Remove the left recursion from A -> A x | y.
2. What problem does left factoring solve?
