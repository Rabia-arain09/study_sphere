---
subject: "Advanced Database Management Systems"
topic: "Recovery, Replication, and Availability"
semester: 4
week: "3"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Recovery, Replication, and Availability

**Definition:** Database recovery restores a consistent state after failure, while replication keeps copies of data on multiple systems.

## Key points
- Write-ahead logs record changes so committed work can be recovered after a crash.
- Replicas can improve availability, but systems must manage how updates are propagated and read.

## Example
After a crash, a database can use its log to redo committed changes that were not yet written to the data file.
