---
subject: Machine Learning
topic: "Artificial Neurons and the Perceptron"
semester: 5
week: "1"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Artificial Neurons and the Perceptron

*Machine Learning · Semester 5 · Week 1 · Difficulty 2/5*

**Key concept:** A perceptron is the simplest artificial neuron: a weighted sum of inputs passed through a step function.

## How it works
- Net input: z = w1x1 + w2x2 + ... + b, or in vector form z = wᵀx + b.
- Output: class 1 if z ≥ 0, otherwise class 0 (or -1).
- Learning rule: w ← w + η (y − ŷ) x. Weights change only when the prediction is wrong; η is the learning rate.
- It converges only if the two classes are **linearly separable**.

## Example

An AND gate is linearly separable, so a perceptron learns it. XOR is not linearly separable, so a single perceptron can never learn it.

## Quick check
1. When does the perceptron update its weights?
2. Why can a single perceptron not learn XOR?
