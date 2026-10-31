---
subject: Machine Learning
topic: "Python Setup for Machine Learning"
semester: 5
week: "1"
difficulty: 1
content_source: ai_generated
content_reviewed: false
---

# Python Setup for Machine Learning

*Machine Learning · Semester 5 · Week 1 · Difficulty 1/5*

**Key concept:** A clean, reproducible Python environment with the core libraries is the first step of every ML project.

## How it works
- Install Python 3 (or Anaconda, which bundles most libraries).
- Create a virtual environment so each project keeps its own library versions.
- Install the core stack: NumPy, pandas, scikit-learn, Matplotlib and Jupyter.
- Always check the installed versions when something behaves differently.

## Example

```bash
python -m venv venv
venv\Scripts\activate
pip install numpy pandas scikit-learn matplotlib jupyter
python -c "import sklearn; print(sklearn.__version__)"
```

## Quick check
1. Why use a virtual environment instead of installing everything globally?
2. Which command installs a library?
