---
subject: Machine Learning
topic: "Density-Based Clustering with DBSCAN"
semester: 5
week: "15"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Density-Based Clustering with DBSCAN

*Machine Learning · Semester 5 · Week 15 · Difficulty 3/5*

**Key concept:** DBSCAN finds clusters as dense regions and labels isolated points as noise.

## How it works
- Two parameters: **eps** (neighbourhood radius) and **min_samples** (points needed to be dense).
- **Core** points have at least min_samples neighbours within eps; **border** points are near a core point; the rest are **noise** (label −1).
- It finds clusters of any shape and needs no k, but struggles when density varies a lot.
- Results are sensitive to eps, and features should be scaled.

## Example

```python
from sklearn.cluster import DBSCAN
db = DBSCAN(eps=0.3, min_samples=5).fit(X)
print(set(db.labels_))   # -1 means noise
```

## Quick check
1. What label does DBSCAN give to noise points?
2. Why can DBSCAN find non-round clusters?
