---
subject: Machine Learning
topic: "Ordinary Least Squares Linear Regression"
semester: 5
week: "14"
difficulty: 3
content_source: lecture
content_reviewed: false
---

# Ordinary Least Squares Linear Regression

*Machine Learning · Semester 5 · Week 14 · Difficulty 3/5*

**Key concept:** OLS finds the line that minimizes the total squared error between actual and predicted values.

## How it works
- It minimizes Σ(y − ŷ)², the sum of squared **residuals** (vertical gaps).
- Slope m = Σ(x − x̄)(y − ȳ) / Σ(x − x̄)². Intercept b = ȳ − m·x̄.
- For simple cases this is a closed-form calculation; for larger models gradient descent can minimize the cost iteratively.
- Gradient descent: start with random m and b, compute the gradient of the cost, adjust slightly to reduce the cost, and repeat until it converges.

## Example

Hours studied x = 2, 4, 6, 8, 10 and scores y = 50, 55, 65, 70, 80. Means: x̄ = 6, ȳ = 64. Σ(x − x̄)² = 40 and Σ(x − x̄)(y − ȳ) = 150. So m = 150 / 40 = 3.75 and b = 64 − 3.75 × 6 = 41.5. The line is **y = 3.75x + 41.5**; for 7 hours the prediction is 67.75.

## Quick check
1. Why are the errors squared?
2. Predict the score for 9 hours of study using y = 3.75x + 41.5.
