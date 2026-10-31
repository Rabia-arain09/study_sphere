---
subject: Compiler Construction
topic: "Role of the Lexical Analyzer and Input Buffering"
semester: 5
week: "2"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Role of the Lexical Analyzer and Input Buffering

*Compiler Construction · Semester 5 · Week 2 · Difficulty 2/5*

**Key concept:** The lexical analyzer reads characters and groups them into tokens for the parser.

## How it works
- A **lexeme** is the actual character sequence, a **token** is its category, and a **pattern** describes the lexemes of a token.
- The lexer also removes whitespace and comments and tracks line numbers.
- **Input buffering:** a two-buffer scheme with a **sentinel** (eof) at the end of each buffer avoids testing the buffer end on every character.
- It needs **lookahead** to know where a lexeme ends.

## Example

Input count = 3 + 5 gives tokens <id, count>, <assign>, <num, 3>, <plus>, <num, 5>. The lexeme count belongs to the token id.

## Quick check
1. What is the difference between a token and a lexeme?
2. What is the purpose of a sentinel in input buffering?
