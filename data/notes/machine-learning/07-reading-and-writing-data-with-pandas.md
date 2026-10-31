---
subject: Machine Learning
topic: "Reading and Writing Data with pandas"
semester: 5
week: "2"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Reading and Writing Data with pandas

*Machine Learning · Semester 5 · Week 2 · Difficulty 2/5*

**Key concept:** pandas loads tabular data into a DataFrame, which is the standard starting point for ML datasets.

## How it works
- pd.read_csv('file.csv') loads a file; df.to_csv('out.csv', index=False) saves one.
- Inspect with df.head(), df.info() and df.describe().
- Select columns with df['col'] and rows with df.loc[label] or df.iloc[position].
- Filter rows with conditions such as df[df['age'] > 20].

## Example

```python
import pandas as pd
df = pd.read_csv('students.csv')
print(df.info())
high = df[df['marks'] > 80]
high.to_csv('high.csv', index=False)
```

## Quick check
1. Which method shows the first five rows?
2. What is the difference between loc and iloc?
