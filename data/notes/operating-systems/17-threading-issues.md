---
subject: Operating Systems
topic: "Threading Issues"
semester: 5
week: "6-7"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Threading Issues

*Operating Systems · Semester 5 · Week 6-7 · Difficulty 3/5*

**Key concept:** Threads raise questions about fork, signals, cancellation and per-thread data.

## How it works
- **fork/exec:** fork may duplicate only the calling thread or all threads. exec replaces the whole process.
- **Signals:** synchronous (for example an illegal memory access) or asynchronous (for example Ctrl-C). The OS must decide which thread receives it.
- **Cancellation:** asynchronous ends the thread at once. **Deferred** waits for a safe cancellation point.
- **Thread-local storage (TLS):** each thread gets its own copy of a variable.

## Example

The C variable errno is thread-local. If it were shared, one thread's failed call could overwrite the error code another thread was about to read.

## Quick check
1. Why is deferred cancellation safer than asynchronous?
2. What is thread-local storage used for?
