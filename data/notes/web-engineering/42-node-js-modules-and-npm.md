---
subject: Web Engineering
topic: "Node.js Modules and NPM"
semester: 5
week: "11-13"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Node.js Modules and NPM

*Web Engineering · Semester 5 · Week 11-13 · Difficulty 2/5*

**Key concept:** Modules split Node code into files, and NPM installs and manages third-party packages.

## How it works
- **Core modules** (fs, http, path) are built in. **Local modules** are your own files. **Third-party** modules come from NPM.
- Export with module.exports and import with require().
- **package.json** lists the project's metadata, scripts and dependencies.
- npm install pkg adds a package to node_modules and package.json. npm init creates package.json.
- dependencies are needed at run time, devDependencies only during development.

## Example

Export and use a function:

```javascript
// add.js
module.exports = (a, b) => a + b;
// app.js
const add = require('./add');
console.log(add(2, 3));  // 5
```

## Quick check
1. What does package.json contain?
2. How do you import a local module in Node?
