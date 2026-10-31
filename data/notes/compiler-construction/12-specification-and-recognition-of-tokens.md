---
subject: Compiler Construction
topic: "Specification and Recognition of Tokens"
semester: 5
week: "2"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Specification and Recognition of Tokens

*Compiler Construction · Semester 5 · Week 2 · Difficulty 3/5*

**Key concept:** Tokens are specified with regular definitions and recognized with transition diagrams.

## How it works
- A **regular definition** names regular expressions so they can be reused.
- A **transition diagram** has states and edges labelled with characters. An accepting state means a token was found.
- Keywords are usually recognized as identifiers first and then checked in a keyword table.
- The lexer uses the **longest match** and skips whitespace.

## Example

letter -> [A-Za-z_]. digit -> [0-9]. id -> letter ( letter | digit )*. The string count1 matches id. The string 1count does not start with a letter, so it is not an id.

## Quick check
1. Why is the longest-match rule needed?
2. How are keywords usually separated from identifiers?
