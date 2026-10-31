---
subject: Operating Systems
topic: "Demand Paging"
semester: 5
week: "16"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Demand Paging

*Operating Systems · Semester 5 · Week 16 · Difficulty 4/5*

**Key concept:** Demand paging loads a page only when it is first used, so a program does not need to be fully in memory.

## How it works
- The **valid-invalid bit** marks whether a page is in memory.
- A **page fault** happens on an invalid reference: trap to the OS, check the access is legal, find a free frame, read the page from disk, update the table, restart the instruction.
- **Effective access time:** EAT = (1 - p) x memory time + p x fault time.
- It works because programs show **locality of reference**.

## Example

Memory access = 200 ns, fault service = 8 ms, p = 1/1000. EAT = 0.999 x 200 + 0.001 x 8,000,000 = about 8200 ns, roughly 41 times slower than no faults. The fault rate must be very low.

## Quick check
1. What triggers a page fault?
2. Why must the page-fault rate be kept very low?
