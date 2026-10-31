---
subject: Operating Systems
topic: "Hardware Support for Synchronization"
semester: 5
week: "11"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Hardware Support for Synchronization

*Operating Systems · Semester 5 · Week 11 · Difficulty 4/5*

**Key concept:** Atomic hardware instructions let software build correct locks.

## How it works
- **test_and_set:** returns the old value and sets the variable to true in one atomic step.
- **compare_and_swap (CAS):** if the value equals the expected one, store the new value. Return the old value.
- **Memory barriers** force earlier reads and writes to finish before later ones.
- **Atomic variables** use CAS to update values safely, for example counters.
- A lock built this way **spins** (busy waits), so it suits short critical sections.

## Example

Each process spins on test_and_set. Only the one that sees false gets the lock; all others see true and keep trying.

```c
while (test_and_set(&lock)) ;  // spin
/* critical section */
lock = false;
```

## Quick check
1. Why must test_and_set be atomic?
2. What does a memory barrier guarantee?
