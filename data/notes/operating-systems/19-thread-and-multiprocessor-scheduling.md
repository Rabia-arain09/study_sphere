---
subject: Operating Systems
topic: "Thread and Multiprocessor Scheduling"
semester: 5
week: "8"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Thread and Multiprocessor Scheduling

*Operating Systems · Semester 5 · Week 8 · Difficulty 4/5*

**Key concept:** With several CPUs, the scheduler must also balance load and keep each thread near its cached data.

## How it works
- **Contention scope:** process-contention scope (user threads compete within a process) or system-contention scope (kernel threads compete system-wide).
- **SMP scheduling:** a common ready queue or one queue per processor.
- **Load balancing:** push migration (a busy CPU pushes work away) and pull migration (an idle CPU takes work).
- **Processor affinity:** soft (preferred) or hard (required) keeps a thread on one CPU so its cache stays warm.
- Affinity and load balancing pull in opposite directions.

## Example

CPU A has 6 threads and CPU B is idle. Pull migration moves one to B and balances load, but that thread loses its cached data on A.

## Quick check
1. Why does processor affinity improve performance?
2. What is the difference between push and pull migration?
