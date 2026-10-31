---
subject: Operating Systems
topic: "Contiguous Memory Allocation"
semester: 5
week: "15"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Contiguous Memory Allocation

*Operating Systems · Semester 5 · Week 15 · Difficulty 3/5*

**Key concept:** Contiguous allocation gives each process one block of memory, and the OS must choose which free hole to use.

## How it works
- **Base and limit registers** protect each process. The MMU checks every address.
- **Strategies:** first fit (first hole big enough), best fit (smallest hole big enough), worst fit (largest hole).
- **External fragmentation:** enough total free space, but scattered. **Compaction** can fix it.
- **Internal fragmentation:** the allocated block is larger than the request.

## Example

Free holes in order: 100K, 500K, 200K, 300K, 600K. A request for 212K goes to 500K under first fit, 300K under best fit and 600K under worst fit.

## Quick check
1. What is the difference between internal and external fragmentation?
2. Which hole does best fit pick?
