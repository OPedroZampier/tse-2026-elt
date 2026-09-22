"""Expectations executadas sobre o dataset exportado."""
from __future__ import annotations

import json
from pathlib import Path

import great_expectations as gx
import pandas as pd

PUBLIC_COLUMNS = {
    "ano_eleicao", "id_candidato", "nome_urna", "nome_candidato", "uf", "cargo",
    "partido", "genero", "raca_cor", "escolaridade", "ocupacao",
    "situacao_candidatura", "data_nascimento", "data_extracao",
}
FORBIDDEN_TOKENS = ("CPF", "CNPJ", "EMAIL", "TITULO_ELEITORAL", "SQ_ELEITOR", "NR_PROCESSO", "NR_DOCUMENTO", "DS_URL")
OPTIONAL_EMPTY = {"motivos_cassacao", "historico_candidaturas"}


def validate_dataset(csv_path: Path, model_name: str = "candidaturas_limpas") -> dict:
    frame = pd.read_csv(csv_path, low_memory=False)
    columns = set(frame.columns)
    if model_name == "candidaturas_limpas" and columns != PUBLIC_COLUMNS:
        raise ValueError(f"Esquema inesperado: ausentes={PUBLIC_COLUMNS-columns}; extras={columns-PUBLIC_COLUMNS}")
    if any(token in col.upper() for col in columns for token in FORBIDDEN_TOKENS):
        raise ValueError("Campo sensível presente na exportação")
    if frame.empty and model_name not in OPTIONAL_EMPTY:
        raise ValueError(f"Dataset vazio: {model_name}")

    context = gx.get_context(mode="ephemeral")
    source = context.data_sources.add_pandas("export")
    asset = source.add_dataframe_asset(name="candidaturas")
    batch_def = asset.add_batch_definition_whole_dataframe("all")
    batch = batch_def.get_batch(batch_parameters={"dataframe": frame})
    expectations = []
    if not frame.empty:
        expectations.append(gx.expectations.ExpectTableRowCountToBeBetween(min_value=1))
    if model_name == "candidaturas_limpas":
        expectations.extend([
            gx.expectations.ExpectColumnValuesToNotBeNull(column="id_candidato"),
            gx.expectations.ExpectColumnValuesToBeUnique(column="id_candidato"),
            gx.expectations.ExpectColumnValuesToNotBeNull(column="uf"),
            gx.expectations.ExpectColumnValuesToNotBeNull(column="cargo"),
            gx.expectations.ExpectColumnValuesToBeBetween(column="ano_eleicao", min_value=2026, max_value=2026),
        ])
    results = [batch.validate(item) for item in expectations]
    summary = {
        "rows_published": int(len(frame)),
        "expectations_passed": sum(bool(result.success) for result in results),
        "expectations_total": len(results),
        "passed": all(bool(result.success) for result in results),
    }
    if "data_extracao" in frame.columns and not frame.empty:
        summary["data_extracao_max"] = str(frame["data_extracao"].max())
    if not summary["passed"]:
        raise ValueError(f"Great Expectations falhou: {json.dumps(summary)}")
    return summary
