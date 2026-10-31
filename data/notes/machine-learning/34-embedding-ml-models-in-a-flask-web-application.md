---
subject: Machine Learning
topic: "Embedding ML Models in a Flask Web Application"
semester: 5
week: "13"
difficulty: 3
content_source: ai_generated
content_reviewed: false
---

# Embedding ML Models in a Flask Web Application

*Machine Learning · Semester 5 · Week 13 · Difficulty 3/5*

**Key concept:** A trained model becomes useful when a web app can load it and return predictions to users.

## How it works
- Train the model, then save it with joblib or pickle.
- Load the saved model once when Flask starts.
- Create a route that receives form input, calls model.predict, and returns the result in a template.
- Store user feedback in SQLite so the model can be retrained later.

## Example

```python
from flask import Flask, request, render_template
import joblib
app = Flask(__name__)
model = joblib.load('model.joblib')

@app.route('/predict', methods=['POST'])
def predict():
    label = model.predict([request.form['text']])[0]
    return render_template('result.html', label=label)
```

## Quick check
1. Why load the model once instead of on every request?
2. Where can feedback be stored for later retraining?
