---
subject: Machine Learning
topic: "Exploring the Housing Dataset"
semester: 5
week: "14"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Exploring the Housing Dataset

*Machine Learning · Semester 5 · Week 14 · Difficulty 2/5*

**Key concept:** Exploring a dataset before modeling shows which features relate to the target and which look unusual.

## How it works
- Check size, types and summary statistics with df.info() and df.describe().
- A **scatterplot matrix** shows relationships between all feature pairs.
- A **correlation matrix** (heatmap) gives a number from −1 to 1; features strongly correlated with the target (price) are good predictors.
- Look for outliers and skewed distributions that may hurt a linear model.

## Example

```python
import seaborn as sns
sns.pairplot(df[['LotArea', 'GrLivArea', 'SalePrice']])
print(df.corr(numeric_only=True)['SalePrice'].sort_values())
```

## Quick check
1. What does a correlation of 0.9 with the target suggest?
2. Why check for outliers before fitting a linear model?
