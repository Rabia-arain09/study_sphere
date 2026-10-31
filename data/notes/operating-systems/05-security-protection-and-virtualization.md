---
subject: Operating Systems
topic: "Security, Protection and Virtualization"
semester: 5
week: "1"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Security, Protection and Virtualization

*Operating Systems · Semester 5 · Week 1 · Difficulty 2/5*

**Key concept:** Protection controls which processes may use which resources. Security defends the system against attack. Virtualization runs several operating systems on one machine.

## How it works
- **Protection** is internal access control, for example file permissions per user and group.
- **Security** also covers outside threats: malware, stolen credentials and denial of service.
- **Privilege escalation** lets a user temporarily act with more rights (for example setuid).
- A **hypervisor** (VMM) creates virtual machines. **Type 1** runs directly on hardware. **Type 2** runs on a host OS.
- Each VM is isolated, so a crash or compromise in one does not directly affect another.

## Example

A script has permissions rwxr-x---. The owner can read, write and run it, the group can read and run it, and others have no access.

```bash
chmod 750 report.sh   # rwx for owner, r-x for group, --- for others
```

## Real-world use

Cloud providers run many customers' virtual machines on the same physical server.

## Quick check
1. What is the difference between protection and security?
2. How do Type 1 and Type 2 hypervisors differ?
