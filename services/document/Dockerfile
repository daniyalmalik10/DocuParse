FROM python:3.11-slim

WORKDIR /app

COPY shared/docuparse_contracts /shared/docuparse_contracts
RUN pip install --no-cache-dir -e /shared/docuparse_contracts

COPY services/document/pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY services/document/app ./app

EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
