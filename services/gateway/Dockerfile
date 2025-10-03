FROM python:3.11-slim

WORKDIR /app

COPY shared/docuparse_contracts /shared/docuparse_contracts
RUN pip install --no-cache-dir -e /shared/docuparse_contracts

COPY services/gateway/pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY services/gateway/app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
