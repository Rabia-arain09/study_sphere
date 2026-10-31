---
subject: Operating Systems
topic: "Linkers and Loaders"
semester: 5
week: "2-3"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Linkers and Loaders

*Operating Systems · Semester 5 · Week 2-3 · Difficulty 3/5*

**Key concept:** A linker combines compiled object files into one executable, and a loader places that executable in memory to run it.

## How it works
- The compiler produces a **relocatable object file** with unresolved symbols.
- The **linker** merges object files and libraries and resolves symbols.
- The **loader** copies the executable into memory, adjusts addresses (**relocation**) and starts it.
- **Static linking** copies library code into the program. **Dynamic linking** (.so, .dll) shares one copy loaded at run time.
- Common executable formats: ELF (Linux), PE (Windows), Mach-O (macOS).

## Example

main.c calls sqrt from the math library. Compiling alone leaves sqrt unresolved in main.o. The link step supplies it.

```bash
gcc -c main.c
gcc main.o -lm -o app
```

## Quick check
1. What does the linker resolve?
2. Give one advantage of dynamic linking.
