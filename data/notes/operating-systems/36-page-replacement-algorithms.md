---
subject: Operating Systems
topic: "Page Replacement Algorithms"
semester: 5
week: "16"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Page Replacement Algorithms

*Operating Systems · Semester 5 · Week 16 · Difficulty 4/5*

**Key concept:** When no frame is free, the OS picks a victim page to evict, and the choice affects the number of page faults.

## How it works
- A **dirty (modify) bit** shows if the victim must be written back to disk first.
- **FIFO:** evict the oldest page. It can suffer **Belady's anomaly**, where more frames cause more faults.
- **Optimal:** evict the page not used for the longest time in the future. Lowest faults, but it needs future knowledge.
- **LRU:** evict the least recently used page. It approximates optimal and has no Belady's anomaly.
- **Approximations:** reference bit, second chance (clock).

## Example

Reference string 7,0,1,2,0,3,0,4,2,3,0,3,2,1,2,0,1,7,0,1 with 3 frames: FIFO gives 15 faults, LRU gives 12 and Optimal gives 9.

## Quick check
1. What is Belady's anomaly?
2. Why can't optimal replacement be used in practice?
