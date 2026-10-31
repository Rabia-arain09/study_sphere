---
subject: Machine Learning
topic: "Selecting Meaningful Features"
semester: 5
week: "6-7"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Selecting Meaningful Features

*Machine Learning · Semester 5 · Week 6-7 · Difficulty 3/5*

**Key concept:** Fewer, more informative features reduce overfitting and speed up training.

## How it works
- Too many features relative to samples causes overfitting (the curse of dimensionality).
- **L1 regularization** pushes useless weights to exactly zero, so it selects features automatically.
- **Sequential Backward Selection (SBS):** start with all features and remove the one that hurts performance least, repeatedly.
- Approaches: filter (statistics), wrapper (search with a model), embedded (built into training, such as L1).

## Example

```python
from sklearn.linear_model import LogisticRegression
lr = LogisticRegression(penalty='l1', solver='liblinear', C=0.1).fit(Xtr, ytr)
print(lr.coef_)   # many weights are exactly 0
```

## Quick check
1. Why does L1 regularization remove features?
2. What does SBS do at each step?
