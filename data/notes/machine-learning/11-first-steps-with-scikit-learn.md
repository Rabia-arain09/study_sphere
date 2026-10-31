---
subject: Machine Learning
topic: "First Steps with scikit-learn"
semester: 5
week: "4-5"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# First Steps with scikit-learn

*Machine Learning · Semester 5 · Week 4-5 · Difficulty 2/5*

**Key concept:** scikit-learn gives every model the same workflow: split, scale, fit, predict, score.

## How it works
- Load data and split it into training and test sets.
- Scale features with StandardScaler (fit on training data only).
- Create a model, call model.fit(X_train, y_train), then model.predict(X_test).
- Measure with accuracy_score or model.score(X_test, y_test).

## Example

```python
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Perceptron
X, y = load_iris(return_X_y=True)
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=1, stratify=y)
sc = StandardScaler().fit(Xtr)
model = Perceptron(eta0=0.1).fit(sc.transform(Xtr), ytr)
print(model.score(sc.transform(Xte), yte))
```

## Quick check
1. Why is the scaler fitted on the training data only?
2. Which method trains a model, and which one makes predictions?
