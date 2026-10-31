---
subject: Machine Learning
topic: "Logistic Regression and Class Probabilities"
semester: 5
week: "4-5"
difficulty: 3
content_source: lecture
content_reviewed: false
---

# Logistic Regression and Class Probabilities

*Machine Learning · Semester 5 · Week 4-5 · Difficulty 3/5*

**Key concept:** Logistic regression is a linear model whose output is squeezed into a 0 to 1 probability.

## How it works
- Compute the net input z = wᵀx + b (as in a perceptron), then apply the **sigmoid** σ(z) = 1 / (1 + e⁻ᶻ).
- The output is a probability. A threshold (usually 0.5) turns it into a class: p ≥ 0.5 means class 1.
- Trained by minimizing **log loss**: cost = −log(p) when the true class is 1 and −log(1 − p) when it is 0. Confident wrong answers are punished hardest.
- Linear regression fails here because a straight line can predict values below 0 or above 1.
- More than two classes: **multinomial logistic regression** uses softmax so all class probabilities sum to 1.
- In scikit-learn, a smaller C means stronger regularization.

## Example

Will a student pass? A model gives p = 0.78 for 6 hours of study, so it predicts Pass. Lowering the threshold catches more positives; raising it demands more confidence.

## Real-world use
- Medical diagnosis (probability of disease)
- Credit scoring (default risk)
- Phishing detection and customer churn

## Quick check
1. Why is the sigmoid used instead of a straight line?
2. What does the 0.5 threshold do?
