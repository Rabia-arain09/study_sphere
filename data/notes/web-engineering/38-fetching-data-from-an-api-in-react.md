---
subject: Web Engineering
topic: "Fetching Data from an API in React"
semester: 5
week: "9-10"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Fetching Data from an API in React

*Web Engineering · Semester 5 · Week 9-10 · Difficulty 3/5*

**Key concept:** A component loads data from an API after it renders, stores it in state and displays it.

## How it works
- Use **fetch** or **axios** inside **useEffect** so the call runs after render.
- Parse the JSON response, then save it in state with the setter.
- Track **loading** and **error** states to show feedback.
- An empty dependency array [] makes the effect run once.

## Example

Show a list of users:

```jsx
const [users, setUsers] = useState([]);
useEffect(() => {
  fetch('/api/users').then(r => r.json()).then(setUsers);
}, []);
return <ul>{users.map(u => <li key={u.id}>{u.name}</li>)}</ul>;
```

## Quick check
1. Why is the fetch placed inside useEffect?
2. What does the empty array [] do?
