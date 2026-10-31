---
subject: Machine Learning
topic: "Plotting with Matplotlib: Line, Bar and Scatter Graphs"
semester: 5
week: "3"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Plotting with Matplotlib: Line, Bar and Scatter Graphs

*Machine Learning · Semester 5 · Week 3 · Difficulty 2/5*

**Key concept:** Matplotlib turns numbers into plots so you can see trends, comparisons and relationships.

## How it works
- Line graph (plt.plot): change over time. Bar graph (plt.bar): compare categories. Scatter (plt.scatter): relationship between two variables.
- Always add a title, axis labels and a legend.
- plt.subplots(rows, cols) draws several plots in one figure.

## Example

```python
import matplotlib.pyplot as plt
fig, ax = plt.subplots(1, 2)
ax[0].plot([1, 2, 3], [2, 4, 8]); ax[0].set_title('Line')
ax[1].scatter([1, 2, 3], [3, 1, 2]); ax[1].set_title('Scatter')
plt.show()
```

## Quick check
1. Which plot suits comparing marks of five subjects?
2. How do you draw two plots side by side?
