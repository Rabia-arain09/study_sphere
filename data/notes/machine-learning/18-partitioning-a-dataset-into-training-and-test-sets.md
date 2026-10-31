---
subject: Machine Learning
topic: "Partitioning a Dataset into Training and Test Sets"
semester: 5
week: "6-7"
difficulty: 1
content_source: ai_generated
content_reviewed: false
---

# Partitioning a Dataset into Training and Test Sets

*Machine Learning · Semester 5 · Week 6-7 · Difficulty 1/5*

**Key concept:** Hold out a test set so you measure performance on data the model has never seen.

## How it works
- train_test_split(X, y, test_size=0.3, random_state=1, stratify=y).
- Common splits: 70/30 or 80/20. Larger training sets teach more; larger test sets measure better.
- stratify=y keeps the class proportions equal in both parts.
- Never fit scalers or imputers on the test set; this is data leakage.

## Example

A model that scores 99% on training data but 70% on test data has overfitted.

## Quick check
1. Why do we need a separate test set?
2. What does stratify=y do?
