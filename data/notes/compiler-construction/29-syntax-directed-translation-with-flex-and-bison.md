---
subject: Compiler Construction
topic: "Syntax-Directed Translation with Flex and Bison"
semester: 5
week: "6"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Syntax-Directed Translation with Flex and Bison

*Compiler Construction · Semester 5 · Week 6 · Difficulty 4/5*

**Key concept:** Flex supplies tokens and Bison supplies the grammar and actions, together forming a working translator.

## How it works
- Flex's yylex() returns token codes and sets yylval to the token's value.
- Bison's rules use $$ for the left side and $1, $2, ... for the symbols on the right.
- Bison generates a header with token codes (bison -d) that the lexer includes.
- You also supply yyerror() and main().

## Example

A tiny calculator. The input 2+3*4 prints 14 because * is declared with higher precedence than +.

```text
/* calc.l */
%{ #include "calc.tab.h" %}
%%
[0-9]+   { yylval = atoi(yytext); return NUM; }
[+*\n]   { return yytext[0]; }
[ \t]    ;
%%

/* calc.y */
%token NUM
%left '+'
%left '*'
%%
line: expr '\n'      { printf("%d\n", $1); } ;
expr: expr '+' expr  { $$ = $1 + $3; }
    | expr '*' expr  { $$ = $1 * $3; }
    | NUM ;
```

## Quick check
1. What does $$ refer to in a Bison action?
2. How does the parser get the numeric value of a NUM token?
