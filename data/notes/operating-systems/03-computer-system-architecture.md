---
subject: Operating Systems
topic: "Computer-System Architecture"
semester: 5
week: "1"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Computer-System Architecture

*Operating Systems · Semester 5 · Week 1 · Difficulty 2/5*

**Key concept:** Systems differ in how many processors they have and how those processors are connected.

## How it works
- **Single-processor:** one general-purpose CPU.
- **Multiprocessor (SMP):** two or more CPUs share the bus and memory. Gains are throughput and graceful degradation, but speedup with n CPUs is less than n.
- **Multicore:** several cores on one chip. On-chip communication is faster and uses less power than separate chips.
- **Clustered:** separate machines joined by a network that share storage, used for high availability.
- **NUMA:** each CPU has local memory, so access time depends on which memory is touched.

## Example

A two-node cluster runs a database. Node A fails, node B notices and takes over, so the service keeps running. In an SMP machine, 4 CPUs typically give less than 4x speedup because of locking and bus contention.

## Quick check
1. What is the main benefit of a clustered system?
2. Why is speedup on n processors usually below n?
