---
subject: Machine Learning
topic: "Assessing Feature Importance with Random Forests"
semester: 5
week: "6-7"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Assessing Feature Importance with Random Forests

*Machine Learning · Semester 5 · Week 6-7 · Difficulty 3/5*

**Key concept:** A random forest ranks features by how much they reduce impurity across all its trees.

## How it works
- A random forest trains many decision trees on random samples of the data and random subsets of the features, then votes.
- feature_importances_ averages how much each feature reduces impurity.
- Use SelectFromModel to keep only features above an importance threshold.
- Correlated features share importance, so a single feature can look less important than it is.

## Example

```python
from sklearn.ensemble import RandomForestClassifier
rf = RandomForestClassifier(n_estimators=500, random_state=1).fit(Xtr, ytr)
print(rf.feature_importances_)
```

## Quick check
1. How does a random forest reduce overfitting compared with one tree?
2. Why can correlated features mislead the importance scores?
