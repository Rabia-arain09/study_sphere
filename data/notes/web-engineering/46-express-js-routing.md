---
subject: Web Engineering
topic: "Express.js Routing"
semester: 5
week: "14-15"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Express.js Routing

*Web Engineering · Semester 5 · Week 14-15 · Difficulty 3/5*

**Key concept:** Express is a minimal framework that maps HTTP methods and paths to handler functions.

## How it works
- Create an app with express(), then define routes: app.get, app.post, app.put, app.delete.
- A handler gets (req, res). Read parameters from req.params, req.query and req.body.
- **Middleware** are functions with (req, res, next) that run before the route handler: logging, parsing JSON (express.json()), authentication.
- **REST** style uses nouns for paths and methods for actions.

## Example

Two routes and a JSON parser:

```javascript
const express = require('express');
const app = express();
app.use(express.json());
app.get('/users/:id', (req, res) => res.json({ id: req.params.id }));
app.post('/users', (req, res) => res.status(201).json(req.body));
app.listen(3000);
```

## Quick check
1. What does next() do in middleware?
2. Where is the :id value available?
