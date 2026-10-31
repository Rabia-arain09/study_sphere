---
subject: Compiler Construction
topic: "Regular Expressions for Lexical Analysis"
semester: 5
week: "2"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Regular Expressions for Lexical Analysis

*Compiler Construction · Semester 5 · Week 2 · Difficulty 3/5*

**Key concept:** Regular expressions describe the patterns of tokens such as identifiers, numbers and keywords.

## How it works
- **Union** a|b, **concatenation** ab, **closure** a* (zero or more).
- Shorthand: a+ (one or more), a? (optional), [a-z] (range).
- Closure binds tighter than concatenation, and concatenation binds tighter than union.
- Each token class gets one regular expression.

## Example

Identifier: [a-zA-Z_][a-zA-Z0-9_]*. Number: [0-9]+(\.[0-9]+)?. So 42 and 3.14 match the number pattern but 3. does not.

## Quick check
1. Write a regular expression for an unsigned integer.
2. Which has higher precedence, closure or union?
