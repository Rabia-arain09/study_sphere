---
subject: Operating Systems
topic: "Real-Time CPU Scheduling"
semester: 5
week: "10"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Real-Time CPU Scheduling

*Operating Systems · Semester 5 · Week 10 · Difficulty 4/5*

**Key concept:** Real-time scheduling must meet deadlines. Hard real-time systems must never miss one, soft real-time systems try to.

## How it works
- A periodic task has processing time t, deadline d and period p, where 0 <= t <= d <= p.
- **Rate-monotonic (RM):** static priority, shorter period means higher priority. Guaranteed if utilization <= N(2^(1/N) - 1).
- **Earliest-deadline-first (EDF):** dynamic priority, the earliest deadline runs first. In theory it can reach 100% utilization.
- **Proportional share:** each task gets a fixed share of CPU time.

## Example

P1 has p = 50 and t = 20. P2 has p = 100 and t = 35. Utilization = 20/50 + 35/100 = 0.75. The RM bound for N = 2 is 2(sqrt(2) - 1) = 0.83, so RM can schedule both.

## Quick check
1. Which task gets higher priority under rate-monotonic scheduling?
2. What is the difference between hard and soft real-time?
