---
subject: Machine Learning
topic: "Performance Evaluation Metrics"
semester: 5
week: "10-11"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Performance Evaluation Metrics

*Machine Learning · Semester 5 · Week 10-11 · Difficulty 3/5*

**Key concept:** Accuracy alone can mislead; the confusion matrix and metrics built from it show what kind of mistakes a model makes.

## How it works
- Confusion matrix: **TP, FP, FN, TN**.
- Precision = TP / (TP + FP): of the predicted positives, how many are right.
- Recall = TP / (TP + FN): of the real positives, how many were found.
- F1 = 2 × precision × recall / (precision + recall). Accuracy = (TP + TN) / total.
- **ROC curve** plots true positive rate against false positive rate; **AUC** is the area under it.

## Example

TP = 40, FP = 10, FN = 20, TN = 30. Precision = 40/50 = 0.80. Recall = 40/60 = 0.67. Accuracy = 70/100 = 0.70. F1 = 0.73.

## Quick check
1. For cancer screening, would you care more about recall or precision? Why?
2. Compute accuracy when TP = 50, TN = 30, FP = 10, FN = 10.
