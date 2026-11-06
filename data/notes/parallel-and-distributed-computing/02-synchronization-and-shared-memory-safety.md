---
subject: "Parallel and Distributed Computing"
topic: "Synchronization and Shared-Memory Safety"
semester: 6
week: "2"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Synchronization and Shared-Memory Safety

**Definition:** Synchronization coordinates concurrent workers that access shared data so operations do not interfere incorrectly.

## Key points
- A race condition occurs when a result depends on the timing of unsynchronized operations.
- Mutexes and semaphores can control access, but poor locking can cause deadlock.

## Example
A mutex can ensure only one thread updates a shared account balance at a time.
