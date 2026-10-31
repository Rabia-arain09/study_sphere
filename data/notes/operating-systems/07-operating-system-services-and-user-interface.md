---
subject: Operating Systems
topic: "Operating-System Services and User Interface"
semester: 5
week: "2-3"
difficulty: 1
content_source: ai_generated
content_reviewed: false
---

# Operating-System Services and User Interface

*Operating Systems · Semester 5 · Week 2-3 · Difficulty 1/5*

**Key concept:** An OS offers services to users and programs, and users reach them through a command line, a graphical interface or touch.

## How it works
- **Services for users:** user interface, program execution, I/O operations, file-system manipulation, communication and error detection.
- **Services for the system itself:** resource allocation, accounting, protection and security.
- **CLI:** a command interpreter (shell) reads commands and either runs built-in code or launches programs.
- **GUI and touch:** windows, icons and gestures built on top of the same services.

## Example

The shell starts two programs and joins them with a pipe. The first lists files and the second counts the lines, so the result is the number of files.

```bash
ls -l | wc -l
```

## Quick check
1. Name two services an OS provides to users.
2. What does a command interpreter do?
