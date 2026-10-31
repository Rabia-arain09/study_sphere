---
subject: Compiler Construction
topic: "Symbol Tables"
semester: 5
week: "1"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Symbol Tables

*Compiler Construction · Semester 5 · Week 1 · Difficulty 3/5*

**Key concept:** A symbol table stores each name with its attributes (type, scope, location) for use during compilation.

## How it works
- Main operations: **insert** a name and **lookup** a name.
- A **hash table** gives near-constant lookup.
- **Scopes** are handled with one table per scope chained together, or a stack of tables. Lookup starts in the innermost scope.
- On leaving a block, its table is discarded or hidden.

## Example

Source: int x; { float x; ... }. Inside the block, lookup(x) finds the inner float. After the block, lookup(x) finds the outer int.

## Quick check
1. Why is lookup started in the innermost scope?
2. Which data structure is commonly used for fast lookup?
