---
subject: Compiler Construction
topic: "The Lex/Flex Lexical-Analyzer Generator"
semester: 5
week: "2"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# The Lex/Flex Lexical-Analyzer Generator

*Compiler Construction · Semester 5 · Week 2 · Difficulty 3/5*

**Key concept:** Lex/Flex turns a list of pattern-action rules into a C scanner.

## How it works
- A file has three parts separated by %%: definitions, rules and user code.
- Each rule is a regular expression followed by a C action.
- Flex picks the **longest match**. On a tie, the **earlier rule** wins, so list keywords before the identifier rule.
- The scanner function is yylex(). The matched text is in yytext.

## Example

This scanner prints a class for each token it finds and ignores whitespace.

```text
%%
[0-9]+      { printf("NUM\n"); }
[a-z]+      { printf("ID\n"); }
[ \t\n]     ;
%%
```

## Quick check
1. What variable holds the matched text?
2. Why must a keyword rule appear before the identifier rule?
