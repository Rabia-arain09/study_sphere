---
subject: Web Engineering
topic: "Component Life Cycle and Hooks"
semester: 5
week: "9-10"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Component Life Cycle and Hooks

*Web Engineering · Semester 5 · Week 9-10 · Difficulty 4/5*

**Key concept:** A component is mounted, updated and unmounted, and hooks let function components work with these stages.

## How it works
- **Class life cycle:** componentDidMount, componentDidUpdate, componentWillUnmount.
- **useState** adds state to a function component.
- **useEffect(fn, deps)** runs after render. [] means once (mount), [x] means when x changes, no array means after every render.
- The function returned from useEffect is a **cleanup** that runs on unmount.
- Rules of hooks: call them at the top level and only in components or custom hooks.

## Example

Start and stop a timer:

```jsx
useEffect(() => {
  const id = setInterval(tick, 1000);
  return () => clearInterval(id);  // cleanup
}, []);
```

## Quick check
1. Which hook replaces componentDidMount?
2. What is the purpose of the cleanup function?
