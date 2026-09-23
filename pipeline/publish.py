"""Cria ou versiona dataset Kaggle após aprovação dos testes."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path


def publish(
    output: Path,
    dataset_id: str,
    public: bool = False,
    create: bool = False,
) -> None:
    metrics = json.loads((output / "metrics.json").read_text(encoding="utf-8"))
    if not metrics.get("passed"):
        raise ValueError("Publicação bloqueada: validação não passou")
    if not os.getenv("KAGGLE_USERNAME") or not os.getenv("KAGGLE_KEY"):
        raise ValueError("Configure KAGGLE_USERNAME e KAGGLE_KEY como segredos do CI")
    metadata = {
        "title": "Brazil Elections 2026 - Clean TSE Data",
        "id": dataset_id,
        "subtitle": "Candidacies, voters, assets, parties and campaign finance",
        "description": "Clean, documented 2026 election tables derived from Brazil's TSE open data. Includes candidacies, assets, electorate aggregates, party accounts, campaign finance and registered polls. Personal identifiers are excluded. Data is provisional. Source: https://dadosabertos.tse.jus.br/.",
        "licenses": [{"name": "CC-BY-4.0"}],
    }
    (output / "dataset-metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    if create:
        # Avoid status lookup for the first publication: Kaggle may deny
        # status access for a dataset that has not been created yet.
        cmd = ["kaggle", "datasets", "create", "-p", str(output)]
        if public:
            cmd.append("-u")
    else:
        status = subprocess.run(["kaggle", "datasets", "status", dataset_id], capture_output=True, text=True)
        if status.returncode == 0:
            cmd = ["kaggle", "datasets", "version", "-p", str(output), "-m", f"Weekly update: {metrics['rows_published']} published rows"]
        else:
            error = (status.stdout + status.stderr).lower()
            if not any(term in error for term in ("404", "not found", "notfound")):
                raise RuntimeError(f"Não foi possível consultar o dataset Kaggle: {status.stderr or status.stdout}")
            cmd = ["kaggle", "datasets", "create", "-p", str(output)]
            if public:
                cmd.append("-u")
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("output"))
    parser.add_argument("--dataset-id", required=True, help="owner/dataset-slug")
    parser.add_argument("--public", action="store_true", help="Somente para criação inicial")
    parser.add_argument("--create", action="store_true", help="Criar o dataset sem consultar o status primeiro")
    args = parser.parse_args()
    publish(args.output, args.dataset_id, args.public, args.create)
