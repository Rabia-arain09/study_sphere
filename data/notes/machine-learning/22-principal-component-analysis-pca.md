---
subject: Machine Learning
topic: "Principal Component Analysis (PCA)"
semester: 5
week: "8-9"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Principal Component Analysis (PCA)

*Machine Learning · Semester 5 · Week 8-9 · Difficulty 4/5*

**Key concept:** PCA is unsupervised dimensionality reduction: it projects data onto the directions that capture the most variance.

## How it works
- Steps: standardize the data, compute the covariance matrix, find its eigenvectors and eigenvalues, sort by eigenvalue, keep the top k, project.
- Each eigenvector is a **principal component**; its eigenvalue is the variance it explains. Components are orthogonal.
- The explained variance ratio tells you how much information each component keeps.
- PCA ignores class labels. It is used for visualization, compression and noise reduction.

## Example

```python
from sklearn.decomposition import PCA
pca = PCA(n_components=2).fit(Xtr_std)
print(pca.explained_variance_ratio_)
```

A 30-feature dataset can often be reduced to 2 or 3 components and still keep most of its variance.

## Quick check
1. Why must the data be standardized before PCA?
2. Does PCA use the class labels?
