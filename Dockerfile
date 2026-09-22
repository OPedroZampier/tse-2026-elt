FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV TSE_DUCKDB_PATH=work/tse.duckdb
CMD ["sh", "-c", "python -m pipeline.ingest && dbt build --project-dir . --profiles-dir . && python -m pipeline.export"]
