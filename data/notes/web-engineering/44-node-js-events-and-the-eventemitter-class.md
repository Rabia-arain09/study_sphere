---
subject: Web Engineering
topic: "Node.js Events and the EventEmitter Class"
semester: 5
week: "14-15"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Node.js Events and the EventEmitter Class

*Web Engineering · Semester 5 · Week 14-15 · Difficulty 3/5*

**Key concept:** Many Node objects emit events, and the EventEmitter class lets you create and listen to your own.

## How it works
- Import with const EventEmitter = require('events').
- **on(name, fn)** registers a listener. **emit(name, ...args)** triggers all listeners in order.
- **once** runs a listener only the first time.
- Listeners run **synchronously** in the order they were added.
- Streams, servers and many core objects extend EventEmitter.

## Example

Emit a custom event:

```javascript
const EventEmitter = require('events');
const e = new EventEmitter();
e.on('order', id => console.log('Order', id));
e.emit('order', 42);  // Order 42
```

## Quick check
1. What is the difference between on and once?
2. In what order do listeners run?
