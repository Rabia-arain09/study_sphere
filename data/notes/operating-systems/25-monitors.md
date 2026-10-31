---
subject: Operating Systems
topic: "Monitors"
semester: 5
week: "11"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Monitors

*Operating Systems · Semester 5 · Week 11 · Difficulty 4/5*

**Key concept:** A monitor is a high-level construct where only one process can be active inside at a time.

## How it works
- The monitor groups shared data with the procedures that use it, so mutual exclusion is built in.
- **Condition variables** support x.wait() and x.signal().
- Unlike a semaphore signal, x.signal() does nothing if no process is waiting.
- Two semantics: **signal-and-wait** and **signal-and-continue**.

## Example

A bounded buffer monitor: put() waits on notFull when the buffer is full, and get() waits on notEmpty when it is empty. Each signals the other after changing the buffer.

```text
monitor Buffer {
  condition notFull, notEmpty;
  void put(item) { if (full) notFull.wait(); add(item); notEmpty.signal(); }
  item get()     { if (empty) notEmpty.wait(); x = remove(); notFull.signal(); return x; }
}
```

## Real-world use

Java's synchronized, wait() and notify() follow the monitor idea.

## Quick check
1. What makes a monitor safer than raw semaphores?
2. What happens if x.signal() runs and nobody is waiting?
