---
subject: Operating Systems
topic: "Multicore Programming and Multithreading Models"
semester: 5
week: "6-7"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Multicore Programming and Multithreading Models

*Operating Systems · Semester 5 · Week 6-7 · Difficulty 3/5*

**Key concept:** A thread is a unit of CPU use inside a process, and multicore chips need threads to run work in parallel.

## How it works
- Each thread has its own ID, program counter, registers and stack. Threads share code, data and open files.
- **Benefits:** responsiveness, resource sharing, economy and scalability.
- **Concurrency** interleaves tasks. **Parallelism** runs them at the same time.
- **Amdahl's law:** speedup <= 1 / (S + (1 - S) / N), where S is the serial fraction.
- **Models:** many-to-one, one-to-one (Linux, Windows) and many-to-many.

## Example

With S = 0.25 and N = 2 cores: speedup = 1 / (0.25 + 0.375) = 1.6. Even with unlimited cores the limit is 1 / 0.25 = 4.

## Quick check
1. What do threads of the same process share?
2. What limits speedup in Amdahl's law?
