---
subject: Web Engineering
topic: "Bootstrap Introduction and Grid System"
semester: 5
week: "2-3"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Bootstrap Introduction and Grid System

*Web Engineering · Semester 5 · Week 2-3 · Difficulty 2/5*

**Key concept:** Bootstrap is a CSS framework with ready-made classes, and its 12-column grid builds responsive layouts.

## How it works
- Add Bootstrap with a <link> to its CSS (and the JS bundle for interactive parts).
- The grid is **container**, then **row**, then **col** classes. Each row has 12 columns.
- **Breakpoints:** sm 576px, md 768px, lg 992px, xl 1200px, xxl 1400px.
- A class such as col-md-6 means: 6 of 12 columns from the md breakpoint up, and full width below it.

## Example

Two columns that stack on phones and sit side by side on tablets and larger:

```html
<div class="container">
  <div class="row">
    <div class="col-12 col-md-6">Left</div>
    <div class="col-12 col-md-6">Right</div>
  </div>
</div>
```

## Quick check
1. How many columns does the Bootstrap grid have?
2. What does col-md-4 do on a phone?
