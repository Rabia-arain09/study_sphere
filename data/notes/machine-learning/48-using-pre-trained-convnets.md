---
subject: Machine Learning
topic: "Using Pre-trained Convnets"
semester: 5
week: "17"
difficulty: 4
content_source: ai_generated
content_reviewed: false
---

# Using Pre-trained Convnets

*Machine Learning · Semester 5 · Week 17 · Difficulty 4/5*

**Key concept:** Transfer learning reuses a network trained on a huge dataset, which works well when your own data is small.

## How it works
- Networks such as VGG16 or ResNet are pretrained on ImageNet and already know edges, textures and shapes.
- **Feature extraction:** freeze the pretrained base and train only a new classifier on top.
- **Fine-tuning:** unfreeze the top layers of the base and train them with a very small learning rate.
- This usually beats training from scratch on small datasets.

## Example

```python
base = tf.keras.applications.VGG16(weights='imagenet', include_top=False, input_shape=(150, 150, 3))
base.trainable = False   # feature extraction
```

## Quick check
1. What is the difference between feature extraction and fine-tuning?
2. Why freeze the base first?
