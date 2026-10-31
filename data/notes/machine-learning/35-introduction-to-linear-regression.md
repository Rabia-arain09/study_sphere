---
subject: Machine Learning
topic: "Introduction to Linear Regression"
semester: 5
week: "14"
difficulty: 2
content_source: lecture
content_reviewed: false
---

# Introduction to Linear Regression

*Machine Learning · Semester 5 · Week 14 · Difficulty 2/5*

**Key concept:** Linear regression predicts a number by fitting the best straight line through the data.

## How it works
- The model is ŷ = wᵀx + b, the same linear formula as the perceptron and Adaline, but the raw value is the prediction (no step function, no sigmoid).
- Classification predicts a category (spam or not). Regression predicts a number (a price, score or temperature).
- "Best fit" means choosing w and b so the line passes as close as possible to every training point.
- **Simple** linear regression uses one feature; **multiple** linear regression uses several.
- Low variability (strong correlation): points hug the line, predictions are accurate. High variability: the line exists but errors are larger.

## Example

Predicting a house price from its size, a trip fare from distance, or crop yield from rainfall.

## Real-world use
- Real estate (house price)
- Ride-hailing (fare and arrival time)
- Retail (sales forecasting)

## Quick check
1. How does regression differ from classification?
2. What is the difference between simple and multiple linear regression?
