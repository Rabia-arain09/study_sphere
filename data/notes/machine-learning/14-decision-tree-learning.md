---
subject: Machine Learning
topic: "Decision Tree Learning"
semester: 5
week: "4-5"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Decision Tree Learning

*Machine Learning · Semester 5 · Week 4-5 · Difficulty 3/5*

**Key concept:** A decision tree classifies by asking a series of yes/no questions about features, like a flowchart.

## How it works
- At each node it picks the split that makes the child groups as pure as possible.
- **Gini impurity** = 1 − Σ pᵢ². **Entropy** = −Σ pᵢ log₂ pᵢ. **Information gain** = parent impurity − weighted child impurity.
- A fully grown tree memorizes the training data (overfitting). Control it with max_depth, min_samples_leaf or pruning.
- Trees are easy to explain and need no feature scaling.

## Example

Predicting Play or Don't Play: a node splits on Outlook; the Overcast branch is 100% Play, so its Gini is 0 and it becomes a leaf.

```python
from sklearn.tree import DecisionTreeClassifier
tree = DecisionTreeClassifier(criterion='gini', max_depth=3).fit(Xtr, ytr)
```

## Quick check
1. What is the Gini impurity of a node containing only one class?
2. Name two ways to stop a tree from overfitting.
