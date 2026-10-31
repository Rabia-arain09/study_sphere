---
subject: Machine Learning
topic: "The Bag-of-Words Model"
semester: 5
week: "12"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# The Bag-of-Words Model

*Machine Learning · Semester 5 · Week 12 · Difficulty 2/5*

**Key concept:** Bag-of-words turns each document into a vector of word counts over a shared vocabulary, ignoring word order.

## How it works
- Build a vocabulary of all unique words; each document becomes a count vector. Most values are 0, so a sparse matrix is used.
- **TF-IDF** = term frequency × inverse document frequency. It lowers the weight of words that appear in almost every document.
- **n-grams** (such as 2-grams) keep a little word order, for example "not good".

## Example

Docs: "the movie was good" and "the movie was bad". Vocabulary = [the, movie, was, good, bad]. Vectors = [1,1,1,1,0] and [1,1,1,0,1].

```python
from sklearn.feature_extraction.text import TfidfVectorizer
vec = TfidfVectorizer(ngram_range=(1, 2))
X = vec.fit_transform(reviews)
```

## Quick check
1. Does bag-of-words keep word order?
2. Why does TF-IDF down-weight very common words?
