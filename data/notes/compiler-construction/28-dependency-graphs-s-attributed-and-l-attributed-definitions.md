---
subject: Compiler Construction
topic: "Dependency Graphs, S-Attributed and L-Attributed Definitions"
semester: 5
week: "6"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Dependency Graphs, S-Attributed and L-Attributed Definitions

*Compiler Construction · Semester 5 · Week 6 · Difficulty 4/5*

**Key concept:** A dependency graph gives a valid evaluation order for attributes, and S- and L-attributed definitions are classes that can be evaluated during parsing.

## How it works
- The **dependency graph** has an edge from attribute b to attribute c if c needs b.
- A **topological order** of the graph is a valid evaluation order. A cycle means the SDD cannot be evaluated.
- **S-attributed:** only synthesized attributes. Fits bottom-up (LR) parsing.
- **L-attributed:** each inherited attribute depends only on the parent's attributes and siblings to its left. Fits a left-to-right depth-first evaluation.

## Example

For A -> X Y, the rule Y.i = f(X.s) is L-attributed because X is to the left of Y. The rule X.i = g(Y.s) is not, because it depends on a sibling to the right.

## Quick check
1. What kind of attributes may an S-attributed definition use?
2. What does a cycle in the dependency graph mean?
