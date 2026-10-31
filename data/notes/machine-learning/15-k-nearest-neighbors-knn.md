---
subject: Machine Learning
topic: "K-Nearest Neighbors (KNN)"
semester: 5
week: "4-5"
difficulty: 2
content_source: lecture
content_reviewed: false
---

# K-Nearest Neighbors (KNN)

*Machine Learning · Semester 5 · Week 4-5 · Difficulty 2/5*

**Key concept:** KNN is a "lazy learner": it has no training step and classifies a point by looking at its k closest stored examples.

## How it works
- Four steps: choose K, compute the distance (usually Euclidean) to every training point, keep the K nearest, then vote by majority.
- Choosing k matters: too small is noisy and overfits; too large blurs the class boundaries. An odd k avoids ties in two-class problems.
- Scale the features, otherwise the feature with the largest numbers dominates the distance.
- Prediction is slow on large datasets because every distance is computed at query time. It also works for regression by averaging.

## Example

With k = 3, a new fruit has 2 apples and 1 banana as nearest neighbours, so it is classified as an apple.

## Quick check
1. Why is KNN called a lazy learner?
2. What goes wrong if k is too small?
