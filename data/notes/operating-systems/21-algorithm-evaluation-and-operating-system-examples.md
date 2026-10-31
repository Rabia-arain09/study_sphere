---
subject: Operating Systems
topic: "Algorithm Evaluation and Operating-System Examples"
semester: 5
week: "10"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Algorithm Evaluation and Operating-System Examples

*Operating Systems · Semester 5 · Week 10 · Difficulty 3/5*

**Key concept:** To choose a scheduling algorithm, evaluate it by modeling, simulation or real implementation.

## How it works
- **Deterministic modeling:** compute results for one fixed workload. Simple, but only valid for that workload.
- **Queueing models:** **Little's formula** n = lambda x W relates queue length, arrival rate and waiting time.
- **Simulation:** run a model with random or trace-driven workloads.
- **Implementation:** most accurate, and most costly.
- **Linux:** the Completely Fair Scheduler tracks virtual runtime in a red-black tree.
- **Windows:** priority-based, preemptive scheduling with 32 priority levels.

## Example

Processes arrive at lambda = 7 per second and spend W = 2 seconds in the queue. By Little's formula, n = 7 x 2 = 14 processes are in the queue on average.

## Quick check
1. State Little's formula.
2. What data structure does the Linux CFS use?
