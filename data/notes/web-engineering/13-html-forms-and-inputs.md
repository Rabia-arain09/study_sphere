---
subject: Web Engineering
topic: "HTML Forms and Inputs"
semester: 5
week: "1"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# HTML Forms and Inputs

*Web Engineering · Semester 5 · Week 1 · Difficulty 2/5*

**Key concept:** Forms collect user input and send it to a server.

## How it works
- <form action="url" method="post"> wraps the controls.
- <input> has types: text, password, email, number, checkbox, radio, submit.
- Other controls: <textarea>, <select> with <option>, <button>.
- Each control needs a **name** so its value is sent. A <label for="id"> improves accessibility.
- Built-in validation: required, minlength, pattern.

## Example

A login form:

```html
<form action="/login" method="post">
  <label for="u">Email</label>
  <input id="u" name="email" type="email" required>
  <input type="submit" value="Log in">
</form>
```

## Quick check
1. Why must an input have a name attribute?
2. Which method is better for sending a password, GET or POST?
