---
subject: Machine Learning
topic: "Robust Regression with RANSAC"
semester: 5
week: "14"
difficulty: 4
content_source: lecture
content_reviewed: false
---

# Robust Regression with RANSAC

*Machine Learning · Semester 5 · Week 14 · Difficulty 4/5*

**Key concept:** OLS is sensitive to outliers; RANSAC fits a line that ignores them.

## How it works
- OLS minimizes squared error, so one far-away point can drag the whole line.
- RANSAC (RANdom SAmple Consensus): 1) randomly pick a small subset and fit a line, 2) measure every point's distance to the line, 3) points within a threshold are **inliers**, 4) repeat many times and keep the line with the most inliers, then refit on those inliers.
- Outliers are excluded from the final fit, not just down-weighted.
- The threshold must be chosen sensibly (residual_threshold).

## Example

```python
from sklearn.linear_model import RANSACRegressor, LinearRegression
ransac = RANSACRegressor(LinearRegression(), max_trials=100, residual_threshold=5.0)
ransac.fit(X, y)
print(ransac.inlier_mask_)
```

## Quick check
1. Why does one outlier hurt OLS so much?
2. What is an inlier in RANSAC?
