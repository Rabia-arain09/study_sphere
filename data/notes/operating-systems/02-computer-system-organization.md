---
subject: Operating Systems
topic: "Computer-System Organization"
semester: 5
week: "1"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Computer-System Organization

*Operating Systems · Semester 5 · Week 1 · Difficulty 2/5*

**Key concept:** The CPU and devices share main memory over a bus, and devices signal the CPU with interrupts instead of being polled.

## How it works
- Each device has a **controller** with a local buffer. A **device driver** hides the controller from the rest of the OS.
- When a device finishes, it raises an **interrupt**. The CPU saves its state, jumps to the handler found through the **interrupt vector**, then resumes.
- **Storage hierarchy:** registers, cache, main memory, SSD, disk. Each level down is larger, slower and cheaper.
- **DMA** lets a controller move whole blocks to memory without CPU involvement per byte.
- A **bootstrap program** in firmware loads the kernel at power-on.

## Example

Reading a 4 KB block: the CPU starts a DMA transfer and runs other work. When the block is in memory, the controller raises one interrupt, instead of 4096 interrupts, one per byte.

## Quick check
1. Why are interrupts better than polling for slow devices?
2. What problem does DMA solve?
