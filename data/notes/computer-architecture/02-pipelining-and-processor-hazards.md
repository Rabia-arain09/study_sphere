---
subject: "Computer Architecture"
topic: "Pipelining and Processor Hazards"
semester: 5
week: "2"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Pipelining and Processor Hazards

**Definition:** Pipelining overlaps stages of several instructions to improve processor throughput, while a hazard is a condition that prevents the next instruction from safely proceeding.

## Key points
- A common pipeline has fetch, decode, execute, memory, and write-back stages.
- Data, control, and structural hazards can require forwarding, stalls, or other handling.

## Example
If one instruction needs a value that the previous instruction has not produced yet, the pipeline may forward the value or insert a stall.
