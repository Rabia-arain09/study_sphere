---
subject: Machine Learning
topic: "Adaptive Linear Neuron (Adaline)"
semester: 5
week: "1"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Adaptive Linear Neuron (Adaline)

*Machine Learning · Semester 5 · Week 1 · Difficulty 3/5*

**Key concept:** Adaline learns by minimizing a smooth cost function with gradient descent, using the raw net input instead of the step output.

## How it works
- Cost function: J(w) = ½ Σ (y − z)², the sum of squared errors.
- Gradient descent update: w ← w + η Σ (y − z) x, computed over the whole training set (batch).
- The cost is convex, so Adaline converges even when the classes are not perfectly separable.
- If η is too large the cost overshoots and diverges; if it is too small learning is very slow. Scaling the features helps convergence.

## Example

Perceptron: compares the class label with the step output and updates after each sample. Adaline: compares the label with the continuous net input and updates using all samples at once.

## Quick check
1. What does Adaline minimize?
2. What happens if the learning rate is too large?
