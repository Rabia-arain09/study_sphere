---
subject: Operating Systems
topic: "Process Concept"
semester: 5
week: "4-5"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Process Concept

*Operating Systems · Semester 5 · Week 4-5 · Difficulty 2/5*

**Key concept:** A process is a program in execution. A program is a passive file, a process is active.

## How it works
- **Memory layout:** text (code), data, heap (grows up) and stack (grows down).
- **States:** new, ready, running, waiting, terminated.
- The **Process Control Block (PCB)** stores the PID, state, program counter, CPU registers, scheduling info, memory info, accounting and I/O status.
- Two processes can run the same program with separate PIDs and memory.

## Example

A running process asks for disk input and moves from running to waiting. When the disk finishes, it moves from waiting to ready, then back to running when the scheduler picks it.

## Quick check
1. What is the difference between a program and a process?
2. Which state does a process enter after requesting I/O?
