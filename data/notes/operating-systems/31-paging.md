---
subject: Operating Systems
topic: "Paging"
semester: 5
week: "15"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Paging

*Operating Systems · Semester 5 · Week 15 · Difficulty 3/5*

**Key concept:** Paging splits memory into fixed-size frames and programs into pages of the same size, removing external fragmentation.

## How it works
- A logical address is a **page number p** and an **offset d**. The page table maps p to a frame.
- Physical address = frame x page size + offset.
- The **TLB** caches page-table entries so most accesses skip the table lookup.
- **Effective access time:** EAT = h x (TLB + m) + (1 - h) x (TLB + 2m) for hit ratio h and memory time m.

## Example

Page size 1 KB, logical address 3000: page = 3000 / 1024 = 2, offset = 3000 - 2048 = 952. If page 2 is in frame 7, the physical address is 7 x 1024 + 952 = 8120. With TLB = 20 ns, m = 100 ns and h = 0.80, EAT = 0.8 x 120 + 0.2 x 220 = 140 ns.

## Quick check
1. Why does paging avoid external fragmentation?
2. What does a TLB hit save?
