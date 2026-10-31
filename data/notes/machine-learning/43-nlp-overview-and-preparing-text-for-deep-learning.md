---
subject: Machine Learning
topic: "NLP Overview and Preparing Text for Deep Learning"
semester: 5
week: "16"
difficulty: 2
content_source: ai_generated
content_reviewed: false
---

# NLP Overview and Preparing Text for Deep Learning

*Machine Learning · Semester 5 · Week 16 · Difficulty 2/5*

**Key concept:** Neural networks need text converted into fixed-length sequences of numbers.

## How it works
- NLP tasks include sentiment analysis, translation, question answering and summarization.
- Steps: tokenize, build a vocabulary that maps each word to an integer, convert each text to a sequence of integers.
- Pad or truncate every sequence to the same length.
- The integer sequence feeds an **embedding layer**, which learns a vector for each word.

## Example

"I love ML" becomes [12, 45, 87] and is padded to [12, 45, 87, 0, 0] for a fixed length of 5.

## Quick check
1. Why must sequences be padded?
2. What does an embedding layer do?
