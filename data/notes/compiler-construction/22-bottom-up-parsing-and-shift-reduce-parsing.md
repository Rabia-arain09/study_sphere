---
subject: Compiler Construction
topic: "Bottom-Up Parsing and Shift-Reduce Parsing"
semester: 5
week: "5"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Bottom-Up Parsing and Shift-Reduce Parsing

*Compiler Construction · Semester 5 · Week 5 · Difficulty 4/5*

**Key concept:** A bottom-up parser reduces the input to the start symbol by building the parse tree from the leaves up.

## How it works
- It uses a stack and four actions: **shift**, **reduce**, **accept**, **error**.
- A **handle** is a substring that matches a production body and whose reduction is a step in a rightmost derivation (in reverse).
- **Conflicts:** shift-reduce (should the parser shift or reduce?) and reduce-reduce (which rule?).
- Bottom-up parsing handles more grammars than top-down.

## Example

Grammar: E -> E + id | id. Input id + id: shift id, reduce E -> id, shift +, shift id, reduce E -> E + id, accept.

## Quick check
1. What is a handle?
2. Name the four parser actions.
