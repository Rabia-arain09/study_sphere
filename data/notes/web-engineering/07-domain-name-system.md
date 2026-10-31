---
subject: Web Engineering
topic: "Domain Name System"
semester: 5
week: "1"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Domain Name System

*Web Engineering · Semester 5 · Week 1 · Difficulty 2/5*

**Key concept:** DNS translates human-readable domain names into IP addresses.

## How it works
- A domain is read right to left: **root**, **TLD** (.com), **second-level** (example), **subdomain** (www).
- A **resolver** asks a chain of name servers: root, TLD, then the domain's authoritative server.
- Answers are **cached** to save time, for a period set by TTL.
- Common records: **A** (IPv4), **AAAA** (IPv6), **CNAME** (alias), **MX** (mail).

## Example

For www.example.com the resolver asks a root server for .com, the .com server for example.com, and the authoritative server returns the A record, for instance 93.184.216.34.

## Quick check
1. What does an A record store?
2. Why does DNS use caching?
