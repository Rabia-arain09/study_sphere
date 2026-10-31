---
subject: Operating Systems
topic: "Structure of the Page Table"
semester: 5
week: "15"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Structure of the Page Table

*Operating Systems · Semester 5 · Week 15 · Difficulty 4/5*

**Key concept:** Page tables for large address spaces need structures that save memory.

## How it works
- A 32-bit space with 4 KB pages has 2^20 entries. At 4 bytes each, one flat table is 4 MB per process.
- **Hierarchical (two-level):** the page table is itself paged. A 32-bit address splits as 10 + 10 + 12 bits.
- **Hashed page table:** hashes the page number, with chaining. Common for spaces over 32 bits.
- **Inverted page table:** one entry per physical frame, keyed by (process ID, page). It saves memory but searching is slower and sharing is harder.

## Example

Two-level paging for a 32-bit address uses 10 bits for the outer table, 10 bits for the inner table and 12 bits for the offset (4 KB pages). Only the inner tables actually used need to exist.

## Quick check
1. Why is a flat page table wasteful for 64-bit systems?
2. What is the trade-off of an inverted page table?
