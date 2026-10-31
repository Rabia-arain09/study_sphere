---
subject: Operating Systems
topic: "Deadlock System Model and Characterization"
semester: 5
week: "13-14"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Deadlock System Model and Characterization

*Operating Systems · Semester 5 · Week 13-14 · Difficulty 3/5*

**Key concept:** A deadlock is a state where each process in a set waits for a resource held by another process in the set.

## How it works
- A process uses a resource in three steps: request, use, release.
- Four conditions must **all** hold: **mutual exclusion**, **hold and wait**, **no preemption**, **circular wait**.
- **Resource-allocation graph:** a request edge P to R, an assignment edge R to P.
- With one instance per resource, a cycle means deadlock. With several instances, a cycle is necessary but not sufficient.

## Example

P1 holds resource A and requests B. P2 holds B and requests A. The graph has a cycle, so both wait forever.

## Quick check
1. List the four necessary conditions for deadlock.
2. When does a cycle in a resource-allocation graph guarantee deadlock?
