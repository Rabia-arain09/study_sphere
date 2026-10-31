---
subject: Operating Systems
topic: "Process Scheduling and Operations on Processes"
semester: 5
week: "4-5"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Process Scheduling and Operations on Processes

*Operating Systems · Semester 5 · Week 4-5 · Difficulty 3/5*

**Key concept:** The scheduler picks which process runs next, and processes are created and ended through system calls.

## How it works
- **Queues:** job queue, ready queue and device queues.
- **Schedulers:** long-term (admits jobs), short-term (picks the next CPU process), medium-term (swaps).
- **Context switch:** save the old process's state in its PCB and load the new one. It is pure overhead.
- **fork()** creates a child copy. **exec()** replaces the child's program. **wait()** lets the parent wait.
- A **zombie** has finished but its parent has not collected it. An **orphan** has lost its parent.

## Example

fork returns 0 in the child and the child's PID in the parent. The child runs ls and the parent waits for it.

```c
pid_t pid = fork();
if (pid == 0) execlp("ls", "ls", NULL);  // child
else wait(NULL);                        // parent
```

## Quick check
1. What value does fork return in the child?
2. Why is a context switch considered overhead?
