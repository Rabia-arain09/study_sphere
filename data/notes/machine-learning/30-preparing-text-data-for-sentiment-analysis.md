---
subject: Machine Learning
topic: "Preparing Text Data for Sentiment Analysis"
semester: 5
week: "12"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# Preparing Text Data for Sentiment Analysis

*Machine Learning · Semester 5 · Week 12 · Difficulty 2/5*

**Key concept:** Raw text must be cleaned and split into tokens before a model can learn from it.

## How it works
- Lowercase the text and remove HTML tags and punctuation (regular expressions help).
- **Tokenize:** split into words. Remove stop words such as the, is, and.
- **Stemming** (Porter) cuts words to a root; **lemmatization** returns the dictionary form.
- The IMDb dataset has 50,000 movie reviews labeled positive or negative.

## Example

"I LOVED this movie!!! <br />" becomes ["loved", "movie"] after cleaning, lowercasing and stop-word removal.

## Quick check
1. Why remove HTML tags from reviews?
2. What is the difference between stemming and lemmatization?
