---
subject: Operating Systems
topic: "Allocation of Frames and Thrashing"
semester: 5
week: "16"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Allocation of Frames and Thrashing

*Operating Systems · Semester 5 · Week 16 · Difficulty 4/5*

**Key concept:** Each process needs enough frames, or it spends more time paging than running (thrashing).

## How it works
- **Allocation:** equal, or proportional: a_i = (s_i / S) x m.
- **Global** replacement takes frames from any process. **Local** replacement takes only from the faulting process.
- **Thrashing:** CPU utilization drops, the OS adds more processes, and things get worse.
- **Working-set model:** WSS is the number of pages used in the last delta references. If the total demand D exceeds the frames available, suspend a process.
- **Page-fault frequency:** add frames above an upper fault rate, remove below a lower one.

## Example

m = 62 frames, with processes of s1 = 10 pages and s2 = 127 pages. Proportional allocation gives a1 = 10/137 x 62 = about 4 frames and a2 = 127/137 x 62 = about 57 frames.

## Quick check
1. What is thrashing?
2. How does the working-set model detect it?
