---
subject: Web Engineering
topic: "Template Engines (EJS)"
semester: 5
week: "14-15"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Template Engines (EJS)

*Web Engineering · Semester 5 · Week 14-15 · Difficulty 3/5*

**Key concept:** A template engine builds HTML on the server by mixing static markup with data.

## How it works
- Set it up with app.set('view engine', 'ejs'), and keep templates in the views folder.
- res.render('page', data) fills the template and sends HTML.
- **EJS tags:** <%= value %> prints an escaped value, <%- html %> prints raw HTML, <% code %> runs JavaScript (loops and conditions).
- **Partials** with include() reuse headers and footers.
- This is **server-side rendering**: the browser receives finished HTML.

## Example

List users in a view:

```html
<!-- views/users.ejs -->
<ul>
<% users.forEach(u => { %>
  <li><%= u.name %></li>
<% }) %>
</ul>

// route: res.render('users', { users })
```

## Quick check
1. What is the difference between <%= %> and <%- %>?
2. What does res.render do?
