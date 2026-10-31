---
subject: Machine Learning
topic: "Dealing with Class Imbalance"
semester: 5
week: "10-11"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Dealing with Class Imbalance

*Machine Learning · Semester 5 · Week 10-11 · Difficulty 3/5*

**Key concept:** When one class is rare, a model can score high accuracy while ignoring it completely.

## How it works
- If 95% of transactions are legitimate, a model that always says legitimate has 95% accuracy and catches no fraud.
- Use recall, F1 or PR-AUC instead of accuracy.
- Use class_weight='balanced' so mistakes on the rare class cost more.
- Resample: **oversample** the minority class (for example SMOTE) or **undersample** the majority class.
- Always use a stratified split.

## Example

```python
from sklearn.linear_model import LogisticRegression
clf = LogisticRegression(class_weight='balanced').fit(Xtr, ytr)
```

## Quick check
1. Why is accuracy a poor metric for fraud detection?
2. Name two ways to handle imbalance.
