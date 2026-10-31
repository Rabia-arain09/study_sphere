---
subject: Machine Learning
topic: "Streamlining Workflows with Pipelines"
semester: 5
week: "10-11"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Streamlining Workflows with Pipelines

*Machine Learning · Semester 5 · Week 10-11 · Difficulty 2/5*

**Key concept:** A pipeline chains preprocessing and a model into one object, which prevents data leakage and simplifies code.

## How it works
- Each step is a (name, transformer) pair; the last step is the model.
- fit() runs fit_transform on every step in turn, and predict() applies the same steps to new data.
- Pipelines work directly with cross_val_score and GridSearchCV, so scaling is refitted inside each fold.

## Example

```python
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
pipe = make_pipeline(StandardScaler(), LogisticRegression())
pipe.fit(Xtr, ytr)
print(pipe.score(Xte, yte))
```

## Quick check
1. How does a pipeline prevent data leakage during cross-validation?
2. What must the last step of a pipeline be?
