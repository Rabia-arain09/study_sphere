---
subject: Compiler Construction
topic: "Syntax-Directed Definitions: Synthesized and Inherited Attributes"
semester: 5
week: "6"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Syntax-Directed Definitions: Synthesized and Inherited Attributes

*Compiler Construction · Semester 5 · Week 6 · Difficulty 4/5*

**Key concept:** A syntax-directed definition (SDD) attaches attributes to grammar symbols and computes them with rules tied to productions.

## How it works
- **Synthesized attribute:** computed from the node's children, so information flows up.
- **Inherited attribute:** computed from the parent or siblings, so information flows down or sideways.
- An **annotated parse tree** shows attribute values on each node.
- Evaluating means applying the rules in an order that respects dependencies.

## Example

Rules: E -> E1 + T gives E.val = E1.val + T.val, and T -> T1 * F gives T.val = T1.val * F.val. For 3 * 5 + 4 the tree gives T.val = 15, then E.val = 19. For a declaration int a, b, the type is inherited: L.inh = T.type is passed down to each identifier.

## Quick check
1. Which attribute type passes information up the tree?
2. Why is the type of a in int a, b an inherited attribute?
