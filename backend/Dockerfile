FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system corvus \
    && adduser --system --ingroup corvus corvus

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=corvus:corvus alembic.ini .
COPY --chown=corvus:corvus migrations ./migrations
COPY --chown=corvus:corvus app ./app

USER corvus

EXPOSE 8000

CMD [ "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]