---
subject: Web Engineering
topic: "CSS Fonts, Element Flow, Float and Position"
semester: 5
week: "2-3"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# CSS Fonts, Element Flow, Float and Position

*Web Engineering · Semester 5 · Week 2-3 · Difficulty 3/5*

**Key concept:** CSS controls fonts and where elements sit, using normal flow, float or the position property.

## How it works
- **Fonts:** font-family (with fallbacks), font-size, font-weight, line-height.
- **Normal flow:** block elements stack vertically, inline elements flow left to right.
- **float** moves an element left or right so text wraps around it. Clear it with clear: both.
- **position:** static (default), relative (offset from its normal place), absolute (relative to the nearest positioned ancestor), fixed (relative to the viewport), sticky.
- **Pseudo-classes** style states, such as a:hover.

## Example

A badge pinned to the corner of a card: give the card position: relative and the badge position: absolute with top and right set to 0.

```css
.card  { position: relative; }
.badge { position: absolute; top: 0; right: 0; }
```

## Quick check
1. What does position: fixed attach an element to?
2. How do you stop the layout from wrapping around a float?
