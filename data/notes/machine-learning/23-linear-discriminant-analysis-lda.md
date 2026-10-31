---
subject: Machine Learning
topic: "Linear Discriminant Analysis (LDA)"
semester: 5
week: "8-9"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Linear Discriminant Analysis (LDA)

*Machine Learning · Semester 5 · Week 8-9 · Difficulty 4/5*

**Key concept:** LDA is supervised dimensionality reduction: it finds directions that best separate the classes.

## How it works
- It maximizes the distance **between** class means while minimizing the spread **within** each class (scatter matrices).
- It can produce at most (number of classes − 1) components.
- It assumes roughly normal features and similar covariance across classes.
- Difference from PCA: LDA uses class labels, PCA does not. This LDA is not Latent Dirichlet Allocation.

## Example

```python
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
lda = LDA(n_components=2).fit(Xtr_std, ytr)
Xtr_lda = lda.transform(Xtr_std)
```

## Quick check
1. How many components can LDA give for a 3-class problem?
2. Give one difference between PCA and LDA.
