---
subject: Compiler Construction
topic: "Syntax Definition and Context-Free Grammars"
semester: 5
week: "1"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Syntax Definition and Context-Free Grammars

*Compiler Construction · Semester 5 · Week 1 · Difficulty 3/5*

**Key concept:** A context-free grammar (CFG) defines the syntax of a language with productions over terminals and non-terminals.

## How it works
- A CFG has four parts: **terminals**, **non-terminals**, **productions** and a **start symbol**.
- A production A -> alpha says A can be replaced by alpha. Grammars are often written in **BNF**.
- A **derivation** starts from the start symbol and applies productions until only terminals remain.
- The language is the set of all terminal strings that can be derived.

## Example

Grammar: list -> list + digit | list - digit | digit, with digit -> 0 | 1 | ... | 9. The string 9-5+2 is derived as list => list + digit => list - digit + digit => digit - digit + digit => 9-5+2.

## Quick check
1. Name the four components of a CFG.
2. What is a derivation?
