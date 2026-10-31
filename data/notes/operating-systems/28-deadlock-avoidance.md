---
subject: Operating Systems
topic: "Deadlock Avoidance"
semester: 5
week: "13-14"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Deadlock Avoidance

*Operating Systems · Semester 5 · Week 13-14 · Difficulty 4/5*

**Key concept:** Avoidance grants a request only if the system stays in a safe state.

## How it works
- A state is **safe** if some order (a safe sequence) lets every process finish. An unsafe state may lead to deadlock.
- **Banker's algorithm** tracks Available, Max, Allocation and Need = Max - Allocation.
- A request is granted only if the resulting state is still safe.
- It needs advance knowledge of each process's maximum demand.

## Example

12 units exist. P0 holds 5 (max 10), P1 holds 2 (max 4), P2 holds 2 (max 9), so Available = 3. P1 needs 2, runs and frees 4, giving 5. P0 needs 5, finishes, giving 10. P2 needs 7 and finishes. The sequence <P1, P0, P2> is safe.

## Quick check
1. What is a safe state?
2. How is Need computed in the banker's algorithm?
