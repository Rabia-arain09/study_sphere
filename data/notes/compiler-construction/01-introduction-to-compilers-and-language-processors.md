---
subject: Compiler Construction
topic: "Introduction to Compilers and Language Processors"
semester: 5
week: "1"
difficulty: 1
content_source: ai_generated
content_reviewed: false
---

# Introduction to Compilers and Language Processors

*Compiler Construction · Semester 5 · Week 1 · Difficulty 1/5*

**Key concept:** A compiler translates a program in a source language into an equivalent program in a target language, usually machine code.

## How it works
- A **compiler** translates the whole program first, then the target program runs on its own.
- An **interpreter** executes the source statement by statement, so it starts quickly but runs slower.
- Many systems mix both: Java compiles to bytecode, then the JVM interprets or JIT-compiles it.
- A **language-processing system** also includes a preprocessor, assembler, linker and loader.
- A compiler must preserve meaning and report errors in the source.

## Example

C source goes through the preprocessor, the compiler (producing assembly), the assembler (object file), and the linker/loader (executable). Python source is instead run directly by the interpreter.

## Quick check
1. What is the main difference between a compiler and an interpreter?
2. Which tools sit before and after the compiler in a language-processing system?
