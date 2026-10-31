---
subject: Operating Systems
topic: "Interprocess Communication"
semester: 5
week: "4-5"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Interprocess Communication

*Operating Systems · Semester 5 · Week 4-5 · Difficulty 3/5*

**Key concept:** Processes exchange data through shared memory or message passing.

## How it works
- **Shared memory:** a region both processes map. It is fast, but the processes must synchronize themselves.
- **Message passing:** send() and receive() through the kernel. It is easier to use and works across machines, but is slower.
- Messages can be direct or through a mailbox, blocking or non-blocking.
- **Pipes** (ordinary: parent-child, one-way; named: FIFO) and **sockets** (IP address and port) are common mechanisms.
- Classic pattern: **producer-consumer** with a bounded buffer.

## Example

A circular buffer of size N = 5 is full when (in + 1) % N == out. This design wastes one slot, so it holds at most 4 items.

## Quick check
1. Why is shared memory faster than message passing?
2. When is a circular buffer full?
