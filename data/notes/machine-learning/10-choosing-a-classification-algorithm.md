---
subject: Machine Learning
topic: "Choosing a Classification Algorithm"
semester: 5
week: "4-5"
difficulty: 2
content_source: lecture
content_reviewed: false
---

# Choosing a Classification Algorithm

*Machine Learning · Semester 5 · Week 4-5 · Difficulty 2/5*

**Key concept:** There is no single best classifier (the "no free lunch" principle); the right choice depends on your data and goal.

## How it works
- **Data size:** some algorithms need lots of data, others work with small datasets.
- **Linear separability:** can a straight line or plane separate the classes, or is the boundary curved?
- **Interpretability:** do you need to explain the decision (a tree) or only predict accurately (a black box)?
- **Training and prediction speed:** some models train instantly but predict slowly, or the opposite.
- Practical steps: select features, pick a performance metric, train several models, compare, then tune the best.

## Example

A bank that must explain loan rejections may prefer a decision tree. A photo tagger that only needs accuracy can use a larger, less interpretable model.

## Quick check
1. Why is there no single best classifier?
2. Name two factors that affect the choice of algorithm.
