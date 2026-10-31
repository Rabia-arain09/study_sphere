---
subject: Machine Learning
topic: "Hierarchical Clustering"
semester: 5
week: "15"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Hierarchical Clustering

*Machine Learning · Semester 5 · Week 15 · Difficulty 3/5*

**Key concept:** Hierarchical clustering builds a tree of clusters, so you do not have to choose k in advance.

## How it works
- **Agglomerative:** start with every point as its own cluster and repeatedly merge the two closest clusters.
- **Linkage** defines cluster distance: single, complete, average or Ward.
- A **dendrogram** shows the merge order; cutting it at a height gives the clusters.
- It becomes slow and memory-heavy on large datasets.

## Example

```python
from sklearn.cluster import AgglomerativeClustering
ac = AgglomerativeClustering(n_clusters=3, linkage='ward').fit(X)
```

## Quick check
1. What does a dendrogram show?
2. Name two linkage methods.
