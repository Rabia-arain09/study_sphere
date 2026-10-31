---
subject: Compiler Construction
topic: "Control Flow and Implementing Three-Address Code"
semester: 5
week: "6"
difficulty: 5
content_source: ai_generated
content_reviewed: false
---

# Control Flow and Implementing Three-Address Code

*Compiler Construction · Semester 5 · Week 6 · Difficulty 5/5*

**Key concept:** Boolean expressions and control-flow statements are translated into conditional and unconditional jumps in three-address code.

## How it works
- Boolean expressions are translated into jumps, using **short-circuit** evaluation for && and ||.
- **Labels** mark jump targets, such as L1: and L2:.
- **Backpatching:** emit a jump with an empty target, keep it in a truelist or falselist, and fill in the label once it is known.
- A while loop uses a label before the test and a jump back at the end.

## Example

if (x < 100 || x > 200 && x != y) x = 0 becomes the code below. A while loop while (x < 10) x = x + 1 becomes: L1: ifFalse x < 10 goto L2; x = x + 1; goto L1; L2:

```text
    if x < 100 goto L2
    ifFalse x > 200 goto L1
    ifFalse x != y goto L1
L2: x = 0
L1:
```

## Quick check
1. Why is backpatching needed?
2. What does short-circuit evaluation mean for ||?
