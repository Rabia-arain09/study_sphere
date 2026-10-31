---
subject: Machine Learning
topic: "Topic Modeling with Latent Dirichlet Allocation"
semester: 5
week: "12"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Topic Modeling with Latent Dirichlet Allocation

*Machine Learning · Semester 5 · Week 12 · Difficulty 4/5*

**Key concept:** Latent Dirichlet Allocation (LDA) discovers hidden topics in a collection of documents without labels.

## How it works
- Each document is a mixture of topics, and each topic is a mixture of words.
- You choose the number of topics; the model returns the top words of each topic.
- It needs raw word counts (CountVectorizer), not TF-IDF.
- Do not confuse it with Linear Discriminant Analysis, which has the same short name.

## Example

```python
from sklearn.decomposition import LatentDirichletAllocation
lda = LatentDirichletAllocation(n_components=5, random_state=1).fit(counts)
```
A topic with top words [goal, match, team, league] can be read as "sport".

## Quick check
1. Is topic modeling supervised or unsupervised?
2. What kind of vectors does LDA need?
