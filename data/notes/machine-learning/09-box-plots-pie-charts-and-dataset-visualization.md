---
subject: Machine Learning
topic: "Box Plots, Pie Charts and Dataset Visualization"
semester: 5
week: "3"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Box Plots, Pie Charts and Dataset Visualization

*Machine Learning · Semester 5 · Week 3 · Difficulty 2/5*

**Key concept:** Different charts answer different questions: spread, proportion and overall distribution.

## How it works
- **Box plot:** shows median, quartiles and outliers, which makes it good for spotting spread and outliers.
- **Pie chart:** shows proportions of a whole; use it only with a few categories.
- **Histogram:** shows how values are distributed. A scatter matrix shows relationships between all feature pairs.
- Visualize a dataset before modeling to catch outliers, skew and strange values.

## Example

```python
df.boxplot(column='marks')          # outliers appear as dots
df['grade'].value_counts().plot.pie()
df['marks'].hist(bins=10)
```

## Quick check
1. What do the dots outside a box plot's whiskers represent?
2. Why is a pie chart a poor choice for 20 categories?
