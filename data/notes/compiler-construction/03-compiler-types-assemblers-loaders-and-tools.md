---
subject: Compiler Construction
topic: "Compiler Types, Assemblers, Loaders and Tools"
semester: 5
week: "1"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Compiler Types, Assemblers, Loaders and Tools

*Compiler Construction · Semester 5 · Week 1 · Difficulty 2/5*

**Key concept:** Compilers differ in how many passes they make, and several helper tools surround them.

## How it works
- **Single-pass:** reads the source once. It is fast and uses little memory, but gives limited optimization.
- **Multi-pass:** builds intermediate forms between passes for better optimization.
- **Preprocessor:** expands macros and includes files.
- **Assembler:** turns assembly into relocatable machine code.
- **Linker and loader:** combine object files and place them in memory.
- **Construction tools:** Lex/Flex (scanners) and Yacc/Bison (parsers).

## Example

A C compiler is multi-pass. Pascal was designed so that a single pass could compile it, because every name must be declared before use.

## Quick check
1. Why can a multi-pass compiler optimize better?
2. What do Lex and Yacc generate?
