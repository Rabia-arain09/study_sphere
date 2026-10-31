---
subject: Compiler Construction
topic: "LR(0) Items and the LR(0) Automaton"
semester: 5
week: "5"
difficulty: 5
content_source: ai_generated
content_reviewed: false
---

# LR(0) Items and the LR(0) Automaton

*Compiler Construction · Semester 5 · Week 5 · Difficulty 5/5*

**Key concept:** An LR(0) item is a production with a dot showing how much has been recognized, and sets of items form the parser's states.

## How it works
- Item A -> alpha . beta means alpha has been seen and beta is expected.
- **Closure:** if an item has the dot before a non-terminal B, add all items B -> . gamma.
- **Goto(I, X):** move the dot over X in each item of I, then take the closure.
- Add an **augmented** production S' -> S to mark acceptance.
- The states and goto edges form the LR(0) automaton.

## Example

Grammar: S' -> S, S -> ( S ) | x. I0 = { S' -> .S, S -> .(S), S -> .x }. Goto(I0, S) = { S' -> S. }. Goto(I0, x) = { S -> x. }. Goto(I0, '(') = { S -> (.S), S -> .(S), S -> .x }.

## Quick check
1. What does the dot in an item mean?
2. What is added by the closure operation?
