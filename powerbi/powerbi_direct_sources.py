"""Prepare the 11 direct ELT inputs for a future private Power BI batch.

This is deliberately not a publisher and does not produce a ready manifest.
The other eight report datasets must be rebuilt and verified before activation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from prepare_powerbi_cloud_batch import split_csv


DIRECT = {
    "bens": "bens/bem_candidato_2026_BRASIL.csv",
    "Candidatos": "candidatos/consulta_cand_2026_BRASIL.csv",
    "Candidatos_Complementar": "candidatos_complementar/consulta_cand_complementar_2026_BRASIL.csv",
    "Coligacoes": "coligacoes/consulta_coligacao_2026_BRASIL.csv",
    "despesas_contratadas": "contas_eleitorais/despesas_contratadas_candidatos_2026_BRASIL.csv",
    "Despesas_Pagas_Eleitorais": "contas_eleitorais/despesas_pagas_candidatos_2026_BRASIL.csv",
    "Despesas_Partidarias": "contas_partidarias/despesa_anual_2026_BRASIL.csv",
    "receitas_candidatos": "contas_eleitorais/receitas_candidatos_2026_BRASIL.csv",
    "Receitas_Partidarias": "contas_partidarias/receita_anual_2026_BRASIL.csv",
    "redes_sociais": "redes_sociais/rede_social_candidato_2026_BRASIL.csv",
    "vagas": "vagas/consulta_vagas_2026_BRASIL.csv",
}


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def prepare(raw: Path, reference: Path, output: Path, mapping=None, max_bytes=40_000_000):
    """Write non-activatable staging files after validating all input headers."""
    mapping = DIRECT if mapping is None else mapping
    if output.exists():
        raise FileExistsError(f"Staging destination already exists: {output}")
    reference_data = json.loads(reference.read_text(encoding="utf-8-sig"))["datasets"]
    if not mapping:
        raise ValueError("No input datasets selected")
    for name, relative in mapping.items():
        if name not in reference_data:
            raise ValueError(f"Missing reference schema: {name}")
        path = raw / relative
        with path.open(encoding="utf-8-sig", newline="") as source:
            header = next(csv.reader(source, delimiter=";"), None)
        if header != reference_data[name]["columns"]:
            raise ValueError(f"Source schema differs from report contract: {name}")
    output.mkdir(parents=True, exist_ok=False)
    datasets = {}
    for name, relative in mapping.items():
        source_path = raw / relative
        before = file_sha256(source_path)
        with source_path.open(encoding="utf-8-sig", newline="") as source:
            datasets[name] = split_csv(source, output / name, max_bytes=max_bytes)
        if file_sha256(source_path) != before:
            raise ValueError(f"Source changed during processing: {name}")
        datasets[name]['source_sha256'] = before
    # Intentionally no manifest.json, no 'ready' status and no cloud writes.
    result = {"status": "incomplete", "publication_allowed": False,
              "reason": "Eight transformed report inputs remain to be rebuilt and verified",
              "datasets": datasets}
    (output / "direct-sources-audit.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit = prepare(args.raw, args.reference, args.output)
    print(f"Prepared {len(audit['datasets'])} direct inputs; batch is not publishable.")
