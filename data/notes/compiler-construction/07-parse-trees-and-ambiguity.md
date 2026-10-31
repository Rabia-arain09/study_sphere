---
subject: Compiler Construction
topic: "Parse Trees and Ambiguity"
semester: 5
week: "1"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Parse Trees and Ambiguity

*Compiler Construction · Semester 5 · Week 1 · Difficulty 3/5*

**Key concept:** A parse tree shows how a string is derived, and a grammar is ambiguous if some string has two parse trees.

## How it works
- The root is the start symbol, interior nodes are non-terminals and leaves are terminals.
- Reading the leaves left to right gives the **yield** (the string).
- **Leftmost** derivation always expands the leftmost non-terminal, and **rightmost** the rightmost.
- An **ambiguous** grammar gives a string more than one parse tree. A compiler needs one meaning, so ambiguity must be removed or resolved.

## Example

Grammar E -> E + E | E * E | id. The string id + id * id has two trees: one groups (id + id) * id and the other id + (id * id). The grammar is ambiguous.

## Quick check
1. How many parse trees does an unambiguous grammar give each string?
2. Show why E -> E + E | E * E | id is ambiguous.
