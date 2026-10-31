---
subject: Web Engineering
topic: "DOM Manipulation"
semester: 5
week: "4-5"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# DOM Manipulation

*Web Engineering · Semester 5 · Week 4-5 · Difficulty 3/5*

**Key concept:** JavaScript can change the page by editing content, attributes, styles and the structure of the DOM.

## How it works
- **Content:** textContent (plain text) and innerHTML (parses HTML, so avoid with untrusted input).
- **Attributes:** setAttribute, getAttribute, classList.add/remove/toggle, element.style.
- **Create and insert:** document.createElement, append, prepend, remove.
- **Traversal:** parentElement, children, nextElementSibling.

## Example

Add a new list item:

```javascript
const li = document.createElement('li');
li.textContent = 'New item';
document.querySelector('ul').append(li);
li.classList.add('highlight');
```

## Quick check
1. Why is innerHTML risky with user input?
2. How do you add a CSS class to an element?
