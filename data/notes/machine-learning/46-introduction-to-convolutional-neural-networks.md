---
subject: Machine Learning
topic: "Introduction to Convolutional Neural Networks"
semester: 5
week: "17"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Introduction to Convolutional Neural Networks

*Machine Learning · Semester 5 · Week 17 · Difficulty 4/5*

**Key concept:** A convolutional network learns small filters that slide over an image to detect patterns.

## How it works
- **Convolution:** a small filter (for example 3 × 3) slides over the image and produces a feature map.
- **Pooling** (max pooling) shrinks the feature map and keeps the strongest responses.
- Typical stack: convolution → ReLU → pooling, repeated, then flatten → dense layers → output.
- The same filter is reused across the image (parameter sharing), so a CNN needs far fewer weights than a fully connected network.
- Early layers detect edges, later layers detect shapes, and the last layers detect objects.

## Example

```python
from tensorflow.keras import layers, models
m = models.Sequential([layers.Conv2D(32, 3, activation='relu', input_shape=(150, 150, 3)),
                       layers.MaxPooling2D(), layers.Flatten(), layers.Dense(1, activation='sigmoid')])
```

## Quick check
1. What does a pooling layer do?
2. Why does a CNN need fewer weights than a dense network on images?
