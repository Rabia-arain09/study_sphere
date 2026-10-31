---
subject: Web Engineering
topic: "Creating a Web Server and Handling HTTP Requests"
semester: 5
week: "14-15"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Creating a Web Server and Handling HTTP Requests

*Web Engineering · Semester 5 · Week 14-15 · Difficulty 3/5*

**Key concept:** Node's http module can create a server that reads each request and writes a response.

## How it works
- http.createServer(callback) runs the callback for each request with **req** and **res**.
- req.url and req.method tell you what was asked for.
- Set the status and headers with res.writeHead, send the body with res.end.
- Simple **routing** is an if/else on req.url. It gets long, which is why Express is popular.

## Example

A server with two routes:

```javascript
const http = require('http');
http.createServer((req, res) => {
  if (req.url === '/') { res.writeHead(200); res.end('Home'); }
  else { res.writeHead(404); res.end('Not found'); }
}).listen(3000);
```

## Quick check
1. What do req and res represent?
2. Which method sends the response body and ends it?
