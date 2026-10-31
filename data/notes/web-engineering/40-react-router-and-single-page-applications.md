---
subject: Web Engineering
topic: "React Router and Single-Page Applications"
semester: 5
week: "9-10"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# React Router and Single-Page Applications

*Web Engineering · Semester 5 · Week 9-10 · Difficulty 4/5*

**Key concept:** A single-page application loads one HTML page and swaps views in the browser, and React Router maps URLs to components.

## How it works
- In an **SPA** the browser does not reload the page. JavaScript updates the view and fetches data.
- **BrowserRouter** wraps the app. **Routes** and **Route** map a path to an element.
- Use **Link** (not <a>) to navigate without a reload.
- Dynamic routes use params, such as /users/:id, read with useParams.
- The server must return index.html for all routes.

## Example

Two pages:

```jsx
<BrowserRouter>
  <Link to="/">Home</Link> <Link to="/about">About</Link>
  <Routes>
    <Route path="/" element={<Home />} />
    <Route path="/about" element={<About />} />
  </Routes>
</BrowserRouter>
```

## Quick check
1. Why use Link instead of an anchor tag?
2. What does the :id in /users/:id mean?
