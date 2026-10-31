---
subject: Web Engineering
topic: "Introduction to React and JSX"
semester: 5
week: "6-8"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Introduction to React and JSX

*Web Engineering · Semester 5 · Week 6-8 · Difficulty 3/5*

**Key concept:** React is a JavaScript library for building user interfaces from reusable components.

## How it works
- React describes the UI as **components** and updates only the parts that change.
- **JSX** is HTML-like syntax inside JavaScript. A build tool (**Babel**) turns it into plain JavaScript.
- **ReactDOM** renders the root component into a DOM element.
- JSX rules: one root element, className instead of class, {} for JavaScript expressions, close all tags.

## Example

A tiny app:

```jsx
function App() {
  const name = 'Sara';
  return <h1 className="title">Hello, {name}</h1>;
}
ReactDOM.createRoot(document.getElementById('root')).render(<App />);
```

## Quick check
1. What does Babel do with JSX?
2. Why is className used instead of class?
