FROM python:3.11-slim

WORKDIR /app

COPY shared/docuparse_contracts /shared/docuparse_contracts
RUN pip install --no-cache-dir -e /shared/docuparse_contracts

COPY services/worker/pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY services/worker/app ./app

CMD ["celery", "-A", "app.celery_app", "worker", "--loglevel=info"]
