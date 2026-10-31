---
subject: Web Engineering
topic: "DOM Introduction and Selecting Elements"
semester: 5
week: "4-5"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# DOM Introduction and Selecting Elements

*Web Engineering · Semester 5 · Week 4-5 · Difficulty 2/5*

**Key concept:** The DOM is the browser's tree of objects for the page, and JavaScript selects nodes from it to read or change them.

## How it works
- The **Document Object Model** represents each tag as a node. document is the root.
- **getElementById('id')** returns one element.
- **querySelector('css')** returns the first match. **querySelectorAll('css')** returns all matches.
- getElementsByClassName and getElementsByTagName return live collections.
- Use console.log to inspect a selected element.

## Example

Select the heading and read its text:

```javascript
const title = document.querySelector('h1');
console.log(title.textContent);
const items = document.querySelectorAll('.item');  // all elements with class item
```

## Quick check
1. What is the difference between querySelector and querySelectorAll?
2. What is the DOM?
