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
    if model_name.endswith(("primeiro_turno", "segundo_turno")):
        expected_round = 2 if model_name.endswith("segundo_turno") else 1
        expectations.extend([
            gx.expectations.ExpectColumnValuesToBeBetween(column="turno", min_value=expected_round, max_value=expected_round),
            gx.expectations.ExpectColumnValuesToBeBetween(column="ano_eleicao", min_value=2026, max_value=2026),
            gx.expectations.ExpectColumnValuesToNotBeNull(column="uf"),
        ])
        if "BR" in set(frame["uf"]):
            raise ValueError("Duplicate national aggregate must not be published")
        if expected_round == 2 and not set(frame["codigo_cargo"]).issubset({1, 3}):
            raise ValueError("Only President and Governor can have runoff results")
        for column in ("votos", "votos_validos", "votos_nominais", "votos_legenda", "comparecimento",
                       "abstencoes", "quociente_eleitoral", "vagas", "quantidade"):
            if column in columns:
                expectations.append(gx.expectations.ExpectColumnValuesToBeBetween(column=column, min_value=0))
        if model_name in ("resultados_primeiro_turno", "resultados_segundo_turno"):
            expectations.append(gx.expectations.ExpectColumnValuesToBeUnique(column="chave_resultado"))
        if model_name in ("votos_candidatos_primeiro_turno", "votos_candidatos_segundo_turno"):
            if frame.duplicated(["chave_resultado", "id_candidato"]).any():
                raise ValueError("Duplicate candidate/territory/office key")
            expectations.append(gx.expectations.ExpectColumnValuesToBeBetween(column="percentual_oficial", min_value=0, max_value=1))
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
