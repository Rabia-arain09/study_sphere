---
subject: Operating Systems
topic: "Deadlock Detection and Recovery"
semester: 5
week: "13-14"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Deadlock Detection and Recovery

*Operating Systems · Semester 5 · Week 13-14 · Difficulty 4/5*

**Key concept:** If deadlock is allowed, the OS must detect it and then recover.

## How it works
- **Single instance:** build a **wait-for graph**. A cycle means deadlock.
- **Multiple instances:** use a detection algorithm similar to the banker's, with Allocation and Request.
- Run detection at every request (costly) or periodically, or when CPU use drops.
- **Recovery by termination:** abort all deadlocked processes, or one at a time until the cycle breaks.
- **Recovery by preemption:** choose a victim, roll it back, and avoid always picking the same victim (starvation).

## Example

The wait-for graph shows P1 waits for P2, P2 waits for P3, and P3 waits for P1. Aborting P3 breaks the cycle.

## Quick check
1. What does a cycle in a wait-for graph mean?
2. Why can resource preemption cause starvation?
