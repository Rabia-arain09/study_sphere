---
subject: Machine Learning
topic: "Hyperparameter Tuning with Grid Search"
semester: 5
week: "10-11"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Hyperparameter Tuning with Grid Search

*Machine Learning · Semester 5 · Week 10-11 · Difficulty 3/5*

**Key concept:** Grid search tries every combination of chosen hyperparameter values and keeps the best by cross-validation.

## How it works
- **Parameters** are learned from data (weights). **Hyperparameters** are set by you (C, k, max_depth).
- GridSearchCV(estimator, param_grid, scoring, cv) evaluates every combination.
- Read the result from best_params_ and best_score_.
- RandomizedSearchCV samples combinations and is cheaper for large search spaces.

## Example

```python
from sklearn.model_selection import GridSearchCV
from sklearn.svm import SVC
gs = GridSearchCV(SVC(), {'C': [0.1, 1, 10], 'kernel': ['linear', 'rbf']}, cv=5)
gs.fit(Xtr, ytr)
print(gs.best_params_)
```

## Quick check
1. What is the difference between a parameter and a hyperparameter?
2. How many models does the grid above train in total?
