---
subject: Web Engineering
topic: "React State and Component Architecture"
semester: 5
week: "9-10"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# React State and Component Architecture

*Web Engineering · Semester 5 · Week 9-10 · Difficulty 4/5*

**Key concept:** State is data owned by a component that changes over time, and changing it re-renders the UI.

## How it works
- Props come **from outside**. State lives **inside** and is changed through a setter (setState or the useState setter).
- Never change state directly. Always use the setter.
- Share state by **lifting it up** to the nearest common parent and passing it down as props.
- The **virtual DOM** lets React compare old and new trees and update only what changed.
- React is **declarative**: you describe what the UI should look like for the current state.

## Example

A counter:

```jsx
function Counter() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(count + 1)}>Clicked {count}</button>;
}
```

## Quick check
1. Why must you not change state directly?
2. What does lifting state up mean?
