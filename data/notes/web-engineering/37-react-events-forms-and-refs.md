---
subject: Web Engineering
topic: "React Events, Forms and Refs"
semester: 5
week: "9-10"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# React Events, Forms and Refs

*Web Engineering · Semester 5 · Week 9-10 · Difficulty 3/5*

**Key concept:** React handles events with camelCase props, controls form inputs through state, and uses refs for direct DOM access.

## How it works
- Events: onClick, onChange, onSubmit. Pass a function, not a call.
- **Controlled component:** the input's value comes from state and onChange updates it.
- Call e.preventDefault() in onSubmit to stop a page reload.
- **Refs** (useRef) point to a DOM element, for example to focus an input.
- Prefer controlled inputs. Use refs sparingly.

## Example

A controlled input:

```jsx
const [name, setName] = useState('');
<input value={name} onChange={e => setName(e.target.value)} />
```

## Quick check
1. What makes an input a controlled component?
2. When is a ref useful?
