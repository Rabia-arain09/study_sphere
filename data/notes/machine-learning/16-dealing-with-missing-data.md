---
subject: Machine Learning
topic: "Dealing with Missing Data"
semester: 5
week: "6-7"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Dealing with Missing Data

*Machine Learning · Semester 5 · Week 6-7 · Difficulty 2/5*

**Key concept:** Real datasets have gaps; you must find them and either remove or fill them before training.

## How it works
- Detect with df.isnull().sum().
- **Remove** rows or columns with df.dropna() when little data is missing.
- **Impute** (fill) with the mean, median or most frequent value using SimpleImputer.
- Fit the imputer on training data only, then transform both train and test.

## Example

```python
from sklearn.impute import SimpleImputer
imp = SimpleImputer(strategy='median')
Xtr = imp.fit_transform(Xtr)
Xte = imp.transform(Xte)
```

## Quick check
1. When is the median a better fill value than the mean?
2. Why should the imputer be fitted on training data only?
