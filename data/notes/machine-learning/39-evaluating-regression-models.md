---
subject: Machine Learning
topic: "Evaluating Regression Models"
semester: 5
week: "14"
difficulty: 3
content_source: lecture
content_reviewed: false
---

# Evaluating Regression Models

*Machine Learning · Semester 5 · Week 14 · Difficulty 3/5*

**Key concept:** Three numbers tell you whether a regression model fits well: MSE, RMSE and R².

## How it works
- **MSE** = mean of (y − ŷ)². **RMSE** = √MSE, which is in the same units as the target.
- **R²** = 1 − SS_res / SS_tot. 1 means a perfect fit; 0 means no better than predicting the mean.
- A **residual plot** should look like random scatter around 0. A curve or funnel shape means the model is missing something.
- Compare training and test errors to detect overfitting.

## Example

If actual = [3, 5, 7] and predicted = [2, 5, 9], residuals are [1, 0, −2]. MSE = (1 + 0 + 4) / 3 = 1.67 and RMSE = 1.29.

## Quick check
1. Why is RMSE easier to interpret than MSE?
2. What does R² = 0 mean?
