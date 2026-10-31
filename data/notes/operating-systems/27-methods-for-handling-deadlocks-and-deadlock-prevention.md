---
subject: Operating Systems
topic: "Methods for Handling Deadlocks and Deadlock Prevention"
semester: 5
week: "13-14"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Methods for Handling Deadlocks and Deadlock Prevention

*Operating Systems · Semester 5 · Week 13-14 · Difficulty 4/5*

**Key concept:** A system can prevent or avoid deadlock, detect and recover from it, or ignore it.

## How it works
- **Ignore it:** the approach in most general-purpose OSs, because deadlocks are rare.
- **Prevention** breaks one necessary condition:
  - Mutual exclusion: cannot be denied for non-sharable resources.
  - Hold and wait: request everything at once (low utilization) or release before asking.
  - No preemption: take resources from waiting processes.
  - Circular wait: give resources a **total order** and request in that order (the most practical).

## Example

Every thread must lock A before B. Since no thread ever holds B while waiting for A, a cycle cannot form.

```python
with lock_a:
    with lock_b:
        do_work()
```

## Quick check
1. Which condition does lock ordering break?
2. Why is denying mutual exclusion usually impossible?
