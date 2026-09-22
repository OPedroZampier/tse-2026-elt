"""Baixa e extrai apenas o CSV nacional de candidaturas do TSE."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from curl_cffi import requests

URL = "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2026.zip"
MEMBER = "consulta_cand_2026_BRASIL.csv"
MIN_BYTES = 10_000


def extract_verified(archive: Path, target: Path) -> dict:
    """Valida ZIP e cabeçalho; substitui o CSV somente após sucesso."""
    with zipfile.ZipFile(archive) as zf:
        names = [name for name in zf.namelist() if Path(name).name == MEMBER]
        if len(names) != 1:
            raise ValueError(f"Esperado um único {MEMBER}; encontrados {len(names)}")
        member = zf.getinfo(names[0])
        if member.file_size < MIN_BYTES:
            raise ValueError("CSV nacional anormalmente pequeno")
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as tmp:
            temp_path = Path(tmp.name)
            try:
                with zf.open(member) as source:
                    shutil.copyfileobj(source, tmp)
            except Exception:
                temp_path.unlink(missing_ok=True)
                raise
    try:
        with temp_path.open("rb") as stream:
            header = stream.readline().decode("latin-1").upper()
        required = ("SQ_CANDIDATO", "ANO_ELEICAO", "SG_UF", "DS_CARGO")
        if not all(field in header for field in required):
            raise ValueError("Cabeçalho TSE sem colunas obrigatórias")
        sha256 = hashlib.sha256(temp_path.read_bytes()).hexdigest()
        os.replace(temp_path, target)
    finally:
        temp_path.unlink(missing_ok=True)
    return {"source_url": URL, "source_csv": MEMBER, "raw_bytes": target.stat().st_size, "sha256": sha256}


def download(target_zip: Path) -> None:
    target_zip.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(URL, impersonate="chrome124", stream=True, timeout=900)
    response.raise_for_status()
    with tempfile.NamedTemporaryFile(dir=target_zip.parent, delete=False) as tmp:
        temp_path = Path(tmp.name)
        try:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    tmp.write(chunk)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise
    try:
        if temp_path.stat().st_size < MIN_BYTES:
            raise ValueError("Download anormalmente pequeno")
        os.replace(temp_path, target_zip)
    finally:
        temp_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, help="Usar ZIP já baixado; útil para teste local")
    parser.add_argument("--workdir", type=Path, default=Path("work"))
    args = parser.parse_args()
    archive = args.archive or args.workdir / "consulta_cand_2026.zip"
    target = args.workdir / MEMBER
    if args.archive is None:
        download(archive)
    metadata = extract_verified(archive, target)
    (args.workdir / "source.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
