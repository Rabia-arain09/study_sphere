---
subject: Web Engineering
topic: "Debugging Node.js Applications"
semester: 5
week: "14-15"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Debugging Node.js Applications

*Web Engineering · Semester 5 · Week 14-15 · Difficulty 3/5*

**Key concept:** Debugging finds why code misbehaves, using logs, the built-in debugger or an editor such as VS Code.

## How it works
- **console.log** is quick but messy. **console.error** and console.table help.
- **Core debugger:** run node inspect app.js and use commands such as n (next), s (step in), c (continue).
- **VS Code:** set **breakpoints** by clicking in the margin, run with the debugger, inspect variables and the call stack.
- **node --inspect** also lets Chrome DevTools connect.
- Read the stack trace from the top to find the failing line.

## Example

Add a breakpoint on the line that computes a total, run in the debugger, and check the variable values at that moment instead of adding many console.log lines.

## Quick check
1. What does a breakpoint do?
2. Which command starts Node's core debugger?
