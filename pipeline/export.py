"""Exporta o modelo DuckDB validado como CSV e Parquet."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from pipeline.validate import validate_dataset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=Path("work/tse.duckdb"))
    parser.add_argument("--output", type=Path, default=Path("output"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    models = sorted(path.stem for path in Path("dbt/models").glob("*.sql"))
    expected_names = {"metrics.json", "dataset-metadata.json"}
    expected_names.update(f"{model}.{extension}" for model in models for extension in ("csv", "parquet"))
    unexpected = {path.name for path in args.output.iterdir()} - expected_names
    if unexpected:
        raise ValueError(f"Arquivos inesperados na pasta de publicação: {sorted(unexpected)}")
    summaries = {}
    with duckdb.connect(str(args.database), read_only=True) as con:
        for model in models:
            csv_path = args.output / f"{model}.csv"
            parquet_path = args.output / f"{model}.parquet"
            con.execute(f"COPY {model} TO '{csv_path.as_posix()}' (HEADER, DELIMITER ',')")
            con.execute(f"COPY {model} TO '{parquet_path.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)")
            summary = validate_dataset(csv_path, model)
            summary["csv_bytes"] = csv_path.stat().st_size
            summary["parquet_bytes"] = parquet_path.stat().st_size
            summaries[model] = summary
    metrics = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "models": summaries,
        "model_count": len(models),
        "rows_published": sum(item["rows_published"] for item in summaries.values()),
        "expectations_passed": sum(item["expectations_passed"] for item in summaries.values()),
        "expectations_total": sum(item["expectations_total"] for item in summaries.values()),
        "passed": all(item["passed"] for item in summaries.values()),
    }
    source_manifest = args.database.parent / "sources.json"
    if source_manifest.exists():
        source = json.loads(source_manifest.read_text(encoding="utf-8"))
        metrics["source_count"] = len(source["sources"])
        metrics["source_files"] = sum(len(item["files"]) for item in source["sources"])
        metrics["physical_source_lines"] = sum(
            file.get("physical_data_lines", 0) for item in source["sources"] for file in item["files"]
        )
        metrics["sources"] = source["sources"]
    (args.output / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "source_count": metrics.get("source_count"),
        "model_count": metrics["model_count"],
        "rows_published": metrics["rows_published"],
        "expectations_passed": metrics["expectations_passed"],
        "expectations_total": metrics["expectations_total"],
        "passed": metrics["passed"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
