---
subject: Machine Learning
topic: "NumPy Arrays"
semester: 5
week: "2"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# NumPy Arrays

*Machine Learning · Semester 5 · Week 2 · Difficulty 2/5*

**Key concept:** NumPy arrays store numbers in fast, fixed-type grids and apply operations to every element at once.

## How it works
- Create with np.array, np.zeros, np.arange; check shape and dtype.
- **Vectorization:** a + b works element by element, with no Python loop.
- Indexing and slicing work per axis: a[1, :] is the second row.
- **Broadcasting** lets arrays of different shapes combine, such as adding a row to every row of a matrix.

## Example

```python
import numpy as np
a = np.array([[1, 2, 3], [4, 5, 6]])
print(a.shape)        # (2, 3)
print(a.mean(axis=0)) # column means: [2.5 3.5 4.5]
```

## Quick check
1. What is the shape of a 2-row, 3-column array?
2. What does axis=0 mean in a.mean(axis=0)?
