---
subject: Operating Systems
topic: "System Calls"
semester: 5
week: "2-3"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# System Calls

*Operating Systems · Semester 5 · Week 2-3 · Difficulty 2/5*

**Key concept:** A system call is how a user program asks the kernel for a service.

## How it works
- Programs normally use an **API** (POSIX, Win32, Java API). The library function then issues the actual system call.
- **Types:** process control, file management, device management, information maintenance, communication and protection.
- **Passing parameters:** in registers, in a memory block whose address is in a register, or on the stack.
- A **trap** switches to kernel mode. The system-call number indexes a table that finds the kernel routine.

## Example

Calling printf in C ends up in the write system call. File descriptor 1 is standard output and 3 is the number of bytes (H, i and newline).

```c
write(1, "Hi\n", 3);
```

## Quick check
1. Why do programs call an API instead of the system call directly?
2. Name three ways to pass parameters to the kernel.
