---
subject: Machine Learning
topic: "Learning and Validation Curves"
semester: 5
week: "10-11"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Learning and Validation Curves

*Machine Learning · Semester 5 · Week 10-11 · Difficulty 3/5*

**Key concept:** Curves help you diagnose whether a model suffers from high bias (underfitting) or high variance (overfitting).

## How it works
- **Learning curve:** accuracy versus training-set size.
- High bias: training and validation accuracy are both low and close together. Fix with a more complex model or better features.
- High variance: training accuracy is high but validation is much lower (a big gap). Fix with more data, regularization or a simpler model.
- **Validation curve:** accuracy versus one hyperparameter, such as C or tree depth.

## Example

A depth-1 tree scoring 60% on both sets is underfitting. A depth-20 tree scoring 100% on training and 75% on validation is overfitting.

## Quick check
1. What does a large gap between training and validation accuracy suggest?
2. Name one fix for high bias.
