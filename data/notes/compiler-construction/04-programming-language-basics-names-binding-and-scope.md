---
subject: Compiler Construction
topic: "Programming Language Basics: Names, Binding and Scope"
semester: 5
week: "1"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Programming Language Basics: Names, Binding and Scope

*Compiler Construction · Semester 5 · Week 1 · Difficulty 2/5*

**Key concept:** Scope rules decide which declaration a name refers to, and binding ties names to storage and values.

## How it works
- A **name** is bound to a storage location, and that location holds a value.
- **Static (lexical) scoping:** the declaration is found from the program text. Most languages use it.
- **Dynamic scoping:** the declaration is found from the chain of active calls at run time.
- **Shadowing:** an inner declaration hides an outer one with the same name.
- Binding can happen at compile time (static) or run time (dynamic).

## Example

x = 1 is global. f() prints x. g() declares its own local x = 2 and then calls f(). With static scoping f prints 1. With dynamic scoping f prints 2.

## Quick check
1. What does f print under dynamic scoping in the example?
2. What is shadowing?
