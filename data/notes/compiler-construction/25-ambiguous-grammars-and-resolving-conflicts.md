---
subject: Compiler Construction
topic: "Ambiguous Grammars and Resolving Conflicts"
semester: 5
week: "5"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Ambiguous Grammars and Resolving Conflicts

*Compiler Construction · Semester 5 · Week 5 · Difficulty 4/5*

**Key concept:** Ambiguous grammars cause parsing conflicts, but precedence rules and default choices can resolve them.

## How it works
- A **shift-reduce** conflict means the parser can both shift and reduce. A **reduce-reduce** conflict means two reductions are possible.
- **Dangling else:** resolve by shifting, so else matches the nearest if.
- **Precedence and associativity** declarations decide operator conflicts.
- Yacc/Bison default: shift for shift-reduce, and the earlier rule for reduce-reduce.

## Example

With E -> E + E | E * E and a state holding E + E . and lookahead *, the parser shifts, because * has higher precedence. With lookahead +, it reduces, because + is left-associative.

```text
%left '+' '-'
%left '*' '/'   /* later line = higher precedence */
```

## Quick check
1. How does a parser resolve the dangling else by default?
2. What default does Yacc use for a reduce-reduce conflict?
