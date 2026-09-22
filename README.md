# TSE 2026 open data pipeline

[Português](README.pt-BR.md) | English

This repository turns the Brazilian Superior Electoral Court's 2026 open data into analysis-ready CSV and Parquet files. A scheduled pipeline downloads the official archives, checks their contents, builds tables in DuckDB with dbt, and validates the exports with Great Expectations.

The current catalog has 14 official archives and produces 22 tables across candidacies, declared assets, the electorate, party accounts, campaign finance, and registered electoral polls. The [source map](docs/SOURCES.md) names every input and output.

## Run it locally

Use Python 3.11 from the repository root:

```bash
python -m venv .venv
# Activate .venv for your shell, then:
python -m pip install -r requirements.txt
python -m pytest -q
python -m pipeline.ingest
dbt build --project-dir . --profiles-dir .
python -m pipeline.export
```

On Windows PowerShell, activate the environment with `.venv\Scripts\Activate.ps1`. If you already have the TSE ZIP files, `python -m pipeline.ingest --archive-dir D:\TSE2026\downloads` reuses them.

The generated files are in `output/`: one CSV and one Parquet file per table, plus `metrics.json`. The raw archives, local DuckDB database, and generated exports stay outside Git. To run the same build in Docker:

```bash
docker build -t tse-2026-elt .
docker run --rm -v "$PWD/output:/app/output" tse-2026-elt
```

## What the pipeline checks

Each archive must contain the expected national CSV files and required columns. The ingestion manifest records source checksums. dbt tests the candidate model; Great Expectations checks every exported table and blocks publication on failed checks. `output/metrics.json` records source counts, published rows, and test results. Its source-line count is a count of physical lines, which can differ from CSV record counts.

The exports omit CPF, CNPJ, email, voter IDs, individual social-media URLs, and process numbers. Donors and suppliers appear only in aggregates. Candidate and party campaign accounts are separate from annual party accounts; their totals should not be added together without an explicit definition.

## Automation and Kaggle

[GitHub Actions](.github/workflows/pipeline.yml) runs on pushes and pull requests, accepts manual runs, and is scheduled for Mondays at 08:17 UTC. Push and pull-request runs upload a validated artifact. Scheduled and manual runs also publish a public Kaggle dataset when these repository settings exist:

- Secrets: `KAGGLE_USERNAME` and `KAGGLE_KEY`
- Variable: `KAGGLE_DATASET_ID` in the form `username/dataset-slug`

Without those settings, Kaggle publication is not active. The [GitLab CI file](.gitlab-ci.yml) supports the same build; its schedule must be configured in GitLab. Dataset downloads can be measured on Kaggle after publication. Pipeline availability comes from the CI run history, not from a number in this README.

## Data source and scope

The source is the [TSE Open Data Portal](https://dadosabertos.tse.jus.br/). See the [source map](docs/SOURCES.md) for the 2026 dataset pages, selected files, and exclusions. TSE data can change; treat each export as a dated snapshot, not a final election result. Credit the TSE when redistributing derived data and check the terms on the official dataset pages.
