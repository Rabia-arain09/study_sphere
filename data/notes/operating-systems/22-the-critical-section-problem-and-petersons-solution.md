---
subject: Operating Systems
topic: "The Critical-Section Problem and Peterson's Solution"
semester: 5
week: "11"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# The Critical-Section Problem and Peterson's Solution

*Operating Systems · Semester 5 · Week 11 · Difficulty 4/5*

**Key concept:** A race condition happens when the result depends on the order of access to shared data, and a critical section protects that access.

## How it works
- counter++ is really three steps: load, add, store. Two threads can interleave them.
- A solution needs **mutual exclusion**, **progress** and **bounded waiting**.
- **Peterson's solution** (two processes) uses flag[2] and turn.
- On modern CPUs, instruction reordering can break it unless memory barriers are used.

## Example

counter = 5 and two threads each run counter++. Both load 5 and both store 6, so the final value is 6 instead of 7.

```c
flag[i] = true; turn = j;
while (flag[j] && turn == j) ;  // wait
/* critical section */
flag[i] = false;
```

## Quick check
1. Name the three requirements for a critical-section solution.
2. Why can Peterson's solution fail on modern hardware?
