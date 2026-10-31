---
subject: Machine Learning
topic: "Word Embeddings"
semester: 5
week: "16"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Word Embeddings

*Machine Learning · Semester 5 · Week 16 · Difficulty 4/5*

**Key concept:** Word embeddings represent each word as a dense vector so that similar words have similar vectors.

## How it works
- One-hot vectors are huge and treat every word as unrelated; embeddings are small and capture meaning.
- **Word2Vec** learns embeddings by predicting a word from its context (CBOW) or context from a word (skip-gram).
- **GloVe** uses global word co-occurrence counts. **FastText** uses sub-word pieces, so it handles rare words.
- **BERT** gives contextual embeddings: the same word gets different vectors in different sentences.
- Famous example: vector(king) − vector(man) + vector(woman) ≈ vector(queen). Pretrained embeddings save training time.

## Example

The word "bank" has one Word2Vec vector, but BERT gives it different vectors in "river bank" and "bank account".

## Quick check
1. Why are embeddings better than one-hot vectors?
2. What advantage does BERT have over Word2Vec?
