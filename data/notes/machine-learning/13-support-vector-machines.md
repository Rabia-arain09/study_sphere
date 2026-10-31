---
subject: Machine Learning
topic: "Support Vector Machines"
semester: 5
week: "4-5"
difficulty: 3
content_source: lecture
content_reviewed: false
---

# Support Vector Machines

*Machine Learning · Semester 5 · Week 4-5 · Difficulty 3/5*

**Key concept:** An SVM finds the separating line (hyperplane) with the widest possible margin between two classes.

## How it works
- Decision function: f(x) = wᵀx + b. The sign of f(x) gives the class; the boundary is wᵀx + b = 0.
- **Margin = 2 / ‖w‖.** Maximizing the margin means minimizing ‖w‖.
- **Support vectors** are the points closest to the boundary; only they determine it.
- **Soft margin:** slack lets some points break the margin. A large C punishes violations (narrow margin); a small C allows more (wider margin).
- **Kernels** handle curved boundaries: linear, polynomial and RBF. For RBF, gamma controls how far one point's influence reaches.
- Scale features first, then tune C and gamma with GridSearchCV.

## Example

Hand-solved example: w = (1, 0) and b = −3 give f(x) = x1 − 3. The support vectors S1 = (2, 0) and S2 = (4, 0) have f = −1 and +1. Margin = 2 / ‖w‖ = 2.

## Quick check
1. Which points define the SVM boundary?
2. What happens to the margin when C is very large?
