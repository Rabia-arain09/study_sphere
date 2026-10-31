---
subject: Machine Learning
topic: "Document Classification with Logistic Regression"
semester: 5
week: "12"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Document Classification with Logistic Regression

*Machine Learning · Semester 5 · Week 12 · Difficulty 3/5*

**Key concept:** Combining TF-IDF features with logistic regression gives a strong, simple baseline for sentiment classification.

## How it works
- Vectorize the reviews, then train LogisticRegression on the vectors.
- Evaluate on a held-out test set with accuracy and a confusion matrix.
- The learned weights show which words push the prediction towards positive or negative.
- Tune C and the n-gram range with GridSearchCV inside a pipeline.

## Example

```python
from sklearn.pipeline import make_pipeline
clf = make_pipeline(TfidfVectorizer(), LogisticRegression(C=10))
clf.fit(train_texts, train_labels)
print(clf.score(test_texts, test_labels))
```

## Quick check
1. How can you find the most positive words in your model?
2. Why put the vectorizer inside the pipeline?
