---
subject: Machine Learning
topic: "K-Fold Cross-Validation"
semester: 5
week: "10-11"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# K-Fold Cross-Validation

*Machine Learning · Semester 5 · Week 10-11 · Difficulty 3/5*

**Key concept:** Cross-validation estimates performance more reliably than a single train/test split by rotating which part is used for testing.

## How it works
- Split the training data into k folds. Train on k − 1 folds, validate on the remaining one, repeat k times, then average.
- k = 10 is a common choice. Use **stratified** k-fold so every fold keeps the class proportions.
- Every sample is used for both training and validation, so the estimate has lower variance.

## Example

```python
from sklearn.model_selection import cross_val_score
scores = cross_val_score(pipe, Xtr, ytr, cv=10)
print(scores.mean(), scores.std())
```

## Quick check
1. With 5-fold CV, how many times is the model trained?
2. Why use stratified folds for classification?
