---
subject: Operating Systems
topic: "Mutex Locks and Semaphores"
semester: 5
week: "11"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Mutex Locks and Semaphores

*Operating Systems · Semester 5 · Week 11 · Difficulty 4/5*

**Key concept:** Mutex locks and semaphores are OS tools that enforce mutual exclusion and ordering.

## How it works
- **Mutex:** acquire() before the critical section, release() after.
- **Semaphore S:** an integer changed only by wait() (decrement, block if it would go negative) and signal() (increment).
- **Binary** semaphores behave like a mutex. **Counting** semaphores guard a pool of n identical resources.
- A blocking implementation puts the process on a waiting queue instead of **busy waiting**.
- Pitfalls: **deadlock** and **priority inversion**.

## Example

A semaphore starts at 3 to guard 3 identical printers. The first three processes pass wait(), and the fourth blocks until one calls signal().

```c
wait(mutex);
/* critical section */
signal(mutex);
```

## Quick check
1. What does a counting semaphore represent?
2. Why does a blocking semaphore avoid busy waiting?
