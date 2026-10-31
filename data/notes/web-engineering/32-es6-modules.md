---
subject: Web Engineering
topic: "ES6 Modules"
semester: 5
week: "6-8"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# ES6 Modules

*Web Engineering · Semester 5 · Week 6-8 · Difficulty 3/5*

**Key concept:** ES6 modules split code into files, each with its own scope, sharing only what it exports.

## How it works
- **export** makes a value available. **import** brings it in.
- **Named exports:** export const a; import { a } from './file.js'.
- **Default export:** one per file; import any name without braces.
- Load in the browser with <script type="module">.
- Modules avoid global name clashes and make dependencies explicit.

## Example

math.js exports add, and app.js imports it:

```javascript
// math.js
export const add = (a, b) => a + b;
export default function square(n) { return n * n; }

// app.js
import square, { add } from './math.js';
```

## Quick check
1. How many default exports can a file have?
2. Which attribute loads a script as a module?
