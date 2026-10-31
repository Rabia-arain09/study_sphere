---
subject: Compiler Construction
topic: "From Regular Expressions to Automata"
semester: 5
week: "2"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# From Regular Expressions to Automata

*Compiler Construction · Semester 5 · Week 2 · Difficulty 4/5*

**Key concept:** A regular expression can be converted mechanically into an NFA, then a DFA, then a smaller DFA.

## How it works
- **Thompson's construction:** builds an NFA piece by piece for union, concatenation and closure using epsilon edges.
- **Subset construction:** each DFA state is a set of NFA states reachable on the same input.
- **DFA minimization:** merge states that behave identically.
- Lex/Flex perform these steps for you.

## Example

For (a|b)*abb the subset construction on the Thompson NFA typically gives a DFA with 5 states. Two of them are equivalent, so minimization leaves the minimal 4-state DFA (one state per progress toward abb).

## Quick check
1. What does each state in the subset construction represent?
2. Why minimize the DFA?
