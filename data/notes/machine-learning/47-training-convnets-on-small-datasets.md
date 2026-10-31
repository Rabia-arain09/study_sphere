---
subject: Machine Learning
topic: "Training Convnets on Small Datasets"
semester: 5
week: "17"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Training Convnets on Small Datasets

*Machine Learning · Semester 5 · Week 17 · Difficulty 4/5*

**Key concept:** With few images a convnet overfits quickly, so you must add variety and limit the model.

## How it works
- **Data augmentation** creates new training images by random rotations, flips, shifts and zooms.
- **Dropout** randomly switches off neurons during training.
- Use a smaller network, and stop with **early stopping** when validation loss stops improving.
- Watch the gap between training and validation accuracy.

## Example

```python
datagen = tf.keras.Sequential([layers.RandomFlip('horizontal'), layers.RandomRotation(0.1), layers.RandomZoom(0.1)])
```

## Quick check
1. Why does augmentation reduce overfitting?
2. What does early stopping do?
