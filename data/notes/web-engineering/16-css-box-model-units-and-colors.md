---
subject: Web Engineering
topic: "CSS Box Model, Units and Colors"
semester: 5
week: "2-3"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# CSS Box Model, Units and Colors

*Web Engineering · Semester 5 · Week 2-3 · Difficulty 2/5*

**Key concept:** Every element is a box made of content, padding, border and margin.

## How it works
- From inside out: **content**, **padding**, **border**, **margin**.
- By default, width sets only the content. With box-sizing: border-box, width includes padding and border.
- **Units:** px (absolute), % (relative to the parent), em (relative to font size), rem (root font size), vw/vh (viewport).
- **Colors:** names, hex (#ff0000), rgb(), rgba() and hsl().

## Example

width: 200px; padding: 10px; border: 5px solid. Default total width = 200 + 2x10 + 2x5 = 230 px. With border-box the total stays 200 px.

```css
.box { width: 200px; padding: 10px; border: 5px solid #333; margin: 20px; }
```

## Quick check
1. What is the total width of the example box with the default box model?
2. What is the difference between em and rem?
