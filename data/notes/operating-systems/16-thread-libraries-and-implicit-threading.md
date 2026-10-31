---
subject: Operating Systems
topic: "Thread Libraries and Implicit Threading"
semester: 5
week: "6-7"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Thread Libraries and Implicit Threading

*Operating Systems · Semester 5 · Week 6-7 · Difficulty 3/5*

**Key concept:** Threads can be created explicitly with a library or managed automatically by the system.

## How it works
- **Libraries:** Pthreads (POSIX), Windows threads, Java threads.
- **Thread pool:** create threads once, reuse them, and cap how many exist.
- **Fork-join:** split a task into subtasks, run them in parallel, then join the results.
- **OpenMP:** compiler directives mark parallel regions.
- **Grand Central Dispatch** (Apple) queues blocks of work for the system to run.

## Example

The parent creates a thread running worker() and then waits for it to finish.

```c
pthread_t tid;
pthread_create(&tid, NULL, worker, NULL);
pthread_join(tid, NULL);
```

## Real-world use

Web servers use thread pools so each request reuses an existing thread instead of paying thread-creation cost.

## Quick check
1. Why use a thread pool?
2. What does pthread_join do?
