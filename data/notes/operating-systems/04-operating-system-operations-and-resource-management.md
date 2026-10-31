---
subject: Operating Systems
topic: "Operating-System Operations and Resource Management"
semester: 5
week: "1"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Operating-System Operations and Resource Management

*Operating Systems · Semester 5 · Week 1 · Difficulty 2/5*

**Key concept:** The OS is interrupt driven. It uses dual-mode operation and a timer to keep control of the CPU, and it manages processes, memory, storage and I/O.

## How it works
- **Dual mode:** a mode bit separates **kernel mode** (0) from **user mode** (1). Privileged instructions run only in kernel mode.
- A **system call** switches to kernel mode. Returning from it switches back to user mode.
- A **timer** is set to interrupt after a fixed time, so one program cannot hold the CPU forever.
- **Process management:** create, delete, suspend, synchronize and communicate.
- **Memory management:** track which parts are in use and decide what to load or remove.
- **Storage and I/O:** file systems, disk scheduling, buffering, caching and drivers.

## Example

The timer is set to 100 ms and a program enters an infinite loop. After 100 ms the timer interrupts, the OS regains control and terminates the program.

## Quick check
1. Why must I/O instructions be privileged?
2. What does the timer protect against?
