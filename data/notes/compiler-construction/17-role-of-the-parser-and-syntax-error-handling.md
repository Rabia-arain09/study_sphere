---
subject: Compiler Construction
topic: "Role of the Parser and Syntax Error Handling"
semester: 5
week: "3"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Role of the Parser and Syntax Error Handling

*Compiler Construction · Semester 5 · Week 3 · Difficulty 3/5*

**Key concept:** The parser checks that the token stream fits the grammar and builds a parse tree, and it must handle errors gracefully.

## How it works
- The parser asks the lexer for tokens one at a time.
- It should report errors clearly, recover and keep parsing, and not slow down correct programs.
- **Panic mode:** skip tokens until a synchronizing token such as a semicolon.
- **Phrase-level:** make a small local fix, such as inserting a missing semicolon.
- **Error productions** and **global correction** are other strategies.

## Example

The input x = 5 y = 6; is missing a semicolon. In panic mode the parser reports an error at y, skips to the next semicolon and continues with the next statement.

## Quick check
1. What does panic-mode recovery do?
2. Name two goals of error handling in a parser.
