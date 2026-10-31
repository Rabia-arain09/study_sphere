---
subject: Compiler Construction
topic: "Top-Down Parsing and Recursive Descent"
semester: 5
week: "3"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Top-Down Parsing and Recursive Descent

*Compiler Construction · Semester 5 · Week 3 · Difficulty 3/5*

**Key concept:** A top-down parser builds the parse tree from the root, using a leftmost derivation. Recursive descent writes one procedure per non-terminal.

## How it works
- The parser expands the start symbol and matches terminals against the input.
- With no lookahead rule it may need **backtracking**.
- A **predictive** parser uses the next token to choose the production, so no backtracking is needed.
- Left-recursive grammars make recursive descent loop forever.

## Example

For expr -> term { + term }, the procedure calls term and loops while the lookahead is +.

```c
void expr() {
    term();
    while (lookahead == '+') { match('+'); term(); }
}
```

## Quick check
1. Why does left recursion break recursive descent?
2. What is a predictive parser?
