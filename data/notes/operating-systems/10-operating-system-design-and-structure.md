---
subject: Operating Systems
topic: "Operating-System Design and Structure"
semester: 5
week: "2-3"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Operating-System Design and Structure

*Operating Systems · Semester 5 · Week 2-3 · Difficulty 3/5*

**Key concept:** An OS can be organized in several ways, trading speed against safety and ease of maintenance.

## How it works
- **Policy vs mechanism:** mechanisms say how something is done, policies say what is done. Keeping them separate adds flexibility.
- **Monolithic:** all services in one kernel. Fast but hard to maintain (traditional Unix, Linux).
- **Layered:** each layer uses only the one below. Easy to debug but adds overhead.
- **Microkernel:** only IPC, basic scheduling and memory in the kernel. Other services run in user space (more secure, slower messaging).
- **Modules:** loadable kernel modules (Linux). **Hybrid:** Windows and macOS mix approaches.

## Example

A network driver crashes. In a monolithic kernel the whole system may go down. In a microkernel the driver is a user-space process, so the OS restarts it and keeps running.

## Quick check
1. What is the main cost of a microkernel?
2. What is the difference between policy and mechanism?
