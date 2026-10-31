---
subject: Compiler Construction
topic: "SLR Parsing Tables"
semester: 5
week: "5"
difficulty: 5
content_source: ai_generated
content_reviewed: false
---

# SLR Parsing Tables

*Compiler Construction · Semester 5 · Week 5 · Difficulty 5/5*

**Key concept:** SLR tables turn the LR(0) automaton into shift, reduce and goto entries, using FOLLOW sets to decide reductions.

## How it works
- **Shift:** for an edge on terminal a from state i to j, put s_j in ACTION[i, a].
- **Reduce:** for an item A -> alpha. in state i, put r (production number) in ACTION[i, a] for every a in FOLLOW(A).
- **Accept:** S' -> S. on $.
- **Goto:** edges on non-terminals fill the GOTO part.
- The parser keeps a stack of states and pops one state per symbol in the reduced body.

## Example

For S -> (S) (rule 1) | x (rule 2): states 0 to 5. In state 3 reduce by rule 2 on ) and $. Parsing (x): shift (, shift x, reduce S -> x, goto state 4, shift ), reduce S -> (S), goto state 1, accept.

## Quick check
1. Why does SLR use FOLLOW sets for reductions?
2. How many states are popped when reducing by S -> ( S )?
