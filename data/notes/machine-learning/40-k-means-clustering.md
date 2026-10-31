---
subject: Machine Learning
topic: "K-Means Clustering"
semester: 5
week: "15"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# K-Means Clustering

*Machine Learning · Semester 5 · Week 15 · Difficulty 3/5*

**Key concept:** K-means groups unlabeled data into k clusters by repeatedly moving centroids to the mean of their points.

## How it works
- Steps: choose k, place k centroids (k-means++ gives good starts), assign each point to the nearest centroid, move each centroid to the mean of its points, repeat until nothing changes.
- **Elbow method:** plot inertia (within-cluster squared distance) against k and pick the bend. **Silhouette score** also helps.
- Scale the features. It prefers round, similar-sized clusters and is sensitive to outliers.

## Example

```python
from sklearn.cluster import KMeans
km = KMeans(n_clusters=3, init='k-means++', random_state=0).fit(X)
print(km.labels_, km.inertia_)
```

## Quick check
1. How does the elbow method choose k?
2. Why does k-means need scaled features?
