---
subject: Operating Systems
topic: "Copy-on-Write"
semester: 5
week: "16"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Copy-on-Write

*Operating Systems · Semester 5 · Week 16 · Difficulty 3/5*

**Key concept:** Copy-on-write lets parent and child share pages until one of them writes, so fork is cheap.

## How it works
- After fork, both processes map the **same frames**, marked copy-on-write.
- On a write, the OS copies **only that page**, gives the writer its own copy and updates its page table.
- If the child calls exec right away, almost nothing is copied.
- **vfork** shares the address space until exec. It is faster but dangerous if the child modifies data.

## Example

A parent has 100 pages and calls fork. The child later modifies 3 pages, so only 3 new frames are allocated instead of 100.

## Quick check
1. When is a page copied under copy-on-write?
2. Why is fork followed by exec especially cheap with copy-on-write?
