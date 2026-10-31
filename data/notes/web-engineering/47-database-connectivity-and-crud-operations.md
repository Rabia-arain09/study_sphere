---
subject: Web Engineering
topic: "Database Connectivity and CRUD Operations"
semester: 5
week: "14-15"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Database Connectivity and CRUD Operations

*Web Engineering · Semester 5 · Week 14-15 · Difficulty 4/5*

**Key concept:** A web app stores its data in a database and uses CRUD operations: create, read, update and delete.

## How it works
- Install a driver or ODM (mysql2, mongodb, mongoose) and connect with a **connection string**.
- **CRUD maps to HTTP:** POST = create, GET = read, PUT/PATCH = update, DELETE = delete.
- Database calls are asynchronous, so use async/await.
- Use **parameterized queries** to prevent SQL injection.
- Keep secrets (passwords, connection strings) in environment variables.

## Example

Read one user from MySQL safely:

```javascript
app.get('/users/:id', async (req, res) => {
  const [rows] = await db.query('SELECT * FROM users WHERE id = ?', [req.params.id]);
  res.json(rows[0]);
});
```

## Quick check
1. Which HTTP method normally maps to Create?
2. Why use a parameterized query?
