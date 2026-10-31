---
subject: Machine Learning
topic: "Feature Scaling"
semester: 5
week: "6-7"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Feature Scaling

*Machine Learning · Semester 5 · Week 6-7 · Difficulty 2/5*

**Key concept:** Scaling puts features on comparable ranges so no feature dominates only because its numbers are bigger.

## How it works
- **Normalization (min-max):** x' = (x − min) / (max − min), giving values from 0 to 1.
- **Standardization:** x' = (x − mean) / std, giving mean 0 and standard deviation 1.
- Needed for KNN, SVM, logistic regression, gradient descent and PCA. Decision trees do not need it.
- Fit the scaler on training data, then apply the same transformation to test data.

## Example

Age (20 to 60) and salary (20,000 to 200,000): without scaling, salary dominates a distance calculation.

## Quick check
1. Which models do not need scaling?
2. What is the formula for standardization?
