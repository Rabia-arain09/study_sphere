---
subject: Operating Systems
topic: "Swapping"
semester: 5
week: "15"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Swapping

*Operating Systems · Semester 5 · Week 15 · Difficulty 2/5*

**Key concept:** Swapping moves processes or pages between main memory and a backing store so total memory demand can exceed physical RAM.

## How it works
- **Standard swapping:** a whole process is rolled out to the backing store and rolled in later.
- Transfer time dominates the cost of a swap.
- **Swapping with paging:** only pages are moved (page out and page in), so it is much cheaper.
- Processes with pending I/O must not be swapped out carelessly.
- **Mobile systems** such as iOS and Android usually do not swap. They ask apps to release memory or terminate them.

## Example

A 100 MB process is swapped out to a disk with a 50 MB/s transfer rate: 100 / 50 = 2 seconds, plus another 2 seconds to swap it back in.

## Quick check
1. Why is swapping whole processes expensive?
2. How do mobile systems cope without swap?
