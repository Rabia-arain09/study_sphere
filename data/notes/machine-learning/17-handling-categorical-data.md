---
subject: Machine Learning
topic: "Handling Categorical Data"
semester: 5
week: "6-7"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Handling Categorical Data

*Machine Learning · Semester 5 · Week 6-7 · Difficulty 2/5*

**Key concept:** Models need numbers, so text categories must be encoded without inventing a false order.

## How it works
- **Ordinal** features have a real order (S < M < L): map them to 0, 1, 2.
- **Nominal** features have no order (colour): use **one-hot encoding**, one 0/1 column per category.
- Label-encoding a nominal feature makes the model think blue > red, which is wrong.
- One-hot with pd.get_dummies or OneHotEncoder; drop one column to avoid redundancy.

## Example

Colour = [red, green, blue] becomes three columns: red=1,0,0; green=0,1,0; blue=0,0,1.

## Quick check
1. Which encoding fits 'T-shirt size' and which fits 'colour'?
2. Why is label encoding wrong for colour?
