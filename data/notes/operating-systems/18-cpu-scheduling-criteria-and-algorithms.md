---
subject: Operating Systems
topic: "CPU Scheduling: Criteria and Algorithms"
semester: 5
week: "8"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# CPU Scheduling: Criteria and Algorithms

*Operating Systems · Semester 5 · Week 8 · Difficulty 3/5*

**Key concept:** The CPU scheduler picks the next ready process, and the algorithm used changes waiting time and fairness.

## How it works
- **Criteria:** CPU utilization, throughput, turnaround time, waiting time, response time.
- **FCFS:** simple, but short jobs can wait behind a long one (convoy effect).
- **SJF:** gives the lowest average waiting time, but needs burst-time estimates. The preemptive form is SRTF.
- **Priority:** can starve low-priority jobs; **aging** fixes this.
- **Round robin:** each process gets a time quantum q, then goes to the back of the queue.
- **Multilevel queue:** separate queues with different algorithms.

## Example

P1, P2 and P3 arrive at time 0 with bursts 24, 3 and 3. FCFS waits are 0, 24 and 27, so the average is 17. SJF runs P2, P3, P1, giving waits 0, 3 and 6, so the average is 3.

## Quick check
1. What is the convoy effect?
2. How does aging prevent starvation?
