---
subject: Compiler Construction
topic: "Associativity and Precedence of Operators"
semester: 5
week: "1"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Associativity and Precedence of Operators

*Compiler Construction · Semester 5 · Week 1 · Difficulty 3/5*

**Key concept:** A grammar can encode operator precedence and associativity by how its non-terminals are layered.

## How it works
- **Left-associative** operators (+, -, *, /) use left recursion: expr -> expr + term.
- **Right-associative** operators (=, ^) use right recursion: right -> letter = right.
- **Precedence:** one non-terminal per level. Lower-precedence operators sit higher in the grammar.
- Parentheses restart from the top: factor -> ( expr ).

## Example

expr -> expr + term | term. term -> term * factor | factor. factor -> ( expr ) | id. In 2 + 3 * 4, * is deeper in the tree, so it binds tighter.

## Quick check
1. Which kind of recursion gives left associativity?
2. Why is * placed deeper in the grammar than +?
