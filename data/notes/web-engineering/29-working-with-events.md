---
subject: Web Engineering
topic: "Working with Events"
semester: 5
week: "4-5"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Working with Events

*Web Engineering · Semester 5 · Week 4-5 · Difficulty 3/5*

**Key concept:** Events let code respond to user actions such as clicks, key presses and form submissions.

## How it works
- Attach a handler with **element.addEventListener('click', handler)**.
- The handler receives an **event object**: event.target is the element that triggered it, event.preventDefault() stops the default action.
- Common events: click, input, change, submit, keydown, mouseover.
- **DOMContentLoaded** fires when the HTML has been parsed. Use it, or put scripts at the end of body.

## Example

Stop a form from reloading the page:

```javascript
form.addEventListener('submit', e => {
  e.preventDefault();
  console.log('Submitted');
});
```

## Quick check
1. What does preventDefault do?
2. What is event.target?
