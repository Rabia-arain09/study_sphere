---
subject: Operating Systems
topic: "Kernel Data Structures and Computing Environments"
semester: 5
week: "1"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Kernel Data Structures and Computing Environments

*Operating Systems · Semester 5 · Week 1 · Difficulty 2/5*

**Key concept:** The kernel relies on basic data structures, and the same OS ideas appear in many computing environments.

## How it works
- **Lists, stacks and queues** hold ready processes, free blocks and pending I/O.
- **Binary search trees** give O(n) worst-case search, or O(log n) when balanced.
- **Hash maps** give O(1) average lookup.
- **Bitmaps** use one bit per resource to show if it is free.
- **Environments:** traditional, mobile, client-server, peer-to-peer, cloud (SaaS, PaaS, IaaS) and real-time embedded.

## Example

A free-frame bitmap reads 1011, where 1 means free. Frames 0, 2 and 3 are free and frame 1 is in use. Finding a free frame is a scan for the first 1.

## Quick check
1. Why is a balanced tree better than a plain binary search tree?
2. Give one example each of client-server and peer-to-peer.
