FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --gid 1000 studysphere \
    && useradd --uid 1000 --gid 1000 --create-home studysphere

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=1000:1000 . .
RUN python -m scripts.ensure_models

USER 1000:1000

EXPOSE 7860

CMD ["gunicorn", "--bind", "0.0.0.0:7860", "wsgi:app"]
