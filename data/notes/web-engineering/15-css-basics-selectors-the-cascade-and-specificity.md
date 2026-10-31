---
subject: Web Engineering
topic: "CSS Basics: Selectors, the Cascade and Specificity"
semester: 5
week: "2-3"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# CSS Basics: Selectors, the Cascade and Specificity

*Web Engineering · Semester 5 · Week 2-3 · Difficulty 2/5*

**Key concept:** CSS styles HTML with rules made of a selector and declarations. The cascade and specificity decide which rule wins.

## How it works
- **Linking:** inline style, internal <style>, or external <link rel="stylesheet">.
- **Selectors:** element (p), class (.card), id (#main), descendant (div p), group (h1, h2).
- **Specificity** from weakest to strongest: element < class < id < inline style.
- With equal specificity, the **later** rule wins. !important overrides, but avoid it.

## Example

p { color: blue; } .note { color: green; } #intro { color: red; }. A paragraph with class note and id intro is red, because the id selector is the most specific.

```css
p      { color: blue; }
.note  { color: green; }
#intro { color: red; }
```

## Quick check
1. Which is more specific, a class selector or an id selector?
2. Name the three ways to add CSS to a page.
