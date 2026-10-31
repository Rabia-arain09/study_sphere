---
subject: Compiler Construction
topic: "Parameter Passing and Aliasing"
semester: 5
week: "1"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Parameter Passing and Aliasing

*Compiler Construction · Semester 5 · Week 1 · Difficulty 3/5*

**Key concept:** The parameter-passing mode decides whether a procedure can change the caller's variables.

## How it works
- **By value:** a copy of the argument is passed. The caller's variable is unchanged.
- **By reference:** the address is passed, so changes affect the caller.
- **By name:** the argument expression is re-evaluated at each use (like macro substitution).
- **Aliasing:** two names refer to the same location, which can make results depend on the mode.

## Example

swap(a, b) with call by value leaves a and b unchanged. With call by reference they are exchanged. Calling f(x, x) by reference makes both parameters aliases of x.

## Quick check
1. Why does swap fail with call by value?
2. What is aliasing?
