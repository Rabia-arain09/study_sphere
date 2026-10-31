---
subject: Web Engineering
topic: "React Components and Props"
semester: 5
week: "9-10"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# React Components and Props

*Web Engineering · Semester 5 · Week 9-10 · Difficulty 3/5*

**Key concept:** Components are reusable pieces of UI, and props are the inputs passed into them.

## How it works
- A **function component** is a function that returns JSX, with a name starting with a capital letter.
- **Props** are passed like attributes and are **read-only**.
- Set defaults with defaultProps or default parameter values. **PropTypes** can check types.
- **Conditional rendering:** {cond && <X />} or a ternary.
- Render lists with map and give each item a unique **key**.

## Example

A reusable card:

```jsx
function Card({ title, price }) {
  return <div><h3>{title}</h3><p>Rs. {price}</p></div>;
}
<Card title="Book" price={500} />
```

## Quick check
1. Can a component change its own props?
2. Why must list items have a key?
