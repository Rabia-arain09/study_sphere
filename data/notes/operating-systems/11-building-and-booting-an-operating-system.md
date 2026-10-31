---
subject: Operating Systems
topic: "Building and Booting an Operating System"
semester: 5
week: "2-3"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Building and Booting an Operating System

*Operating Systems · Semester 5 · Week 2-3 · Difficulty 2/5*

**Key concept:** Booting is the chain of steps that takes a machine from power-on to a running kernel.

## How it works
- **Building:** choose kernel options, compile the kernel and modules, install them. Many systems ship a ready-built kernel.
- **Boot:** firmware (BIOS or UEFI) runs a power-on self-test, then loads a **bootstrap loader** such as GRUB.
- The loader loads the **kernel** into memory and starts it.
- The kernel initializes devices and starts the first process (init or systemd).
- **Debugging:** logs, core dumps, crash dumps and tracing tools such as strace and perf.

## Example

Boot order on Linux: firmware, GRUB, kernel, init/systemd, login prompt. The kernel messages from this process can be read afterward.

```bash
dmesg | head
```

## Quick check
1. What does the bootstrap loader load?
2. Which tool shows kernel boot messages on Linux?
