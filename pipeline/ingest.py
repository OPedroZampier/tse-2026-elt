"""Baixa e verifica todas as famílias CSV relevantes do TSE."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from curl_cffi import requests

from pipeline.sources import BY_KEY, SOURCES, Source


def canonicalize_csv(path: Path) -> int:
    """Regrava CSV válido em dialeto uniforme para arquivos TSE irregulares."""
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        rows = 0
        with path.open("r", encoding="utf-8", newline="") as source, temporary.open(
            "w", encoding="utf-8", newline=""
        ) as target:
            reader = csv.reader(source, delimiter=";", quotechar='"')
            writer = csv.writer(target, delimiter=";", quotechar='"', lineterminator="\n")
            expected = None
            for row in reader:
                if expected is None:
                    expected = len(row)
                if len(row) != expected:
                    raise ValueError(f"{path.name}: linha com {len(row)} colunas; esperado {expected}")
                writer.writerow(row)
                rows += 1
        os.replace(temporary, path)
        return rows - 1
    finally:
        temporary.unlink(missing_ok=True)


def fetch(source: Source, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(source.url, impersonate="chrome124", stream=True, timeout=1800)
    response.raise_for_status()
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=dest.parent, delete=False) as handle:
            temporary = Path(handle.name)
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
        with zipfile.ZipFile(temporary) as archive:
            if not archive.namelist():
                raise ValueError(f"ZIP vazio: {source.key}")
        os.replace(temporary, dest)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def extract(source: Source, archive_path: Path, raw_root: Path) -> dict:
    files = []
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        for member_name in source.members:
            matches = [name for name in names if Path(name).name == member_name]
            if len(matches) != 1:
                raise ValueError(f"{source.key}: esperado {member_name} uma vez, encontrado {len(matches)}")
            member = archive.getinfo(matches[0])
            if member.file_size < 100:
                raise ValueError(f"{source.key}/{member_name}: arquivo pequeno demais")
            target = raw_root / source.key / member_name
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as handle:
                    temporary = Path(handle.name)
                    with archive.open(member) as stream:
                        header = stream.readline()
                        columns = header.decode("latin-1").upper()
                        if not all(required in columns for required in source.required):
                            raise ValueError(f"{source.key}/{member_name}: cabeçalho inesperado")
                        handle.write(header.decode("latin-1").encode("utf-8"))
                        digest = hashlib.sha256()
                        digest.update(header)
                        physical_lines = header.count(b"\n")
                        while chunk := stream.read(1024 * 1024):
                            handle.write(chunk.decode("latin-1").encode("utf-8"))
                            digest.update(chunk)
                            physical_lines += chunk.count(b"\n")
                os.replace(temporary, target)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
            if source.key == "contas_partidarias" and member_name.startswith("receita_anual_"):
                canonicalize_csv(target)
            files.append({
                "name": member_name,
                "bytes_utf8": target.stat().st_size,
                "source_sha256": digest.hexdigest(),
                "physical_data_lines": max(0, physical_lines - 1),
            })
    return {"source": source.key, "url": source.url, "archive_bytes": archive_path.stat().st_size, "files": files}


def ingest(workdir: Path, archive_dir: Path | None = None, keys: list[str] | None = None) -> dict:
    selected = [BY_KEY[key] for key in keys] if keys else SOURCES
    manifest = {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "sources": []}
    for source in selected:
        archive_path = (archive_dir / source.archive_name) if archive_dir and (archive_dir / source.archive_name).exists() else workdir / "zips" / source.archive_name
        if not archive_path.exists():
            print(f"Baixando {source.key}: {source.url}", flush=True)
            fetch(source, archive_path)
        print(f"Extraindo {source.key}", flush=True)
        manifest["sources"].append(extract(source, archive_path, workdir / "raw"))
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "sources.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", type=Path, default=Path("work"))
    parser.add_argument("--archive-dir", type=Path)
    parser.add_argument("--only", nargs="+", choices=sorted(BY_KEY))
    args = parser.parse_args()
    manifest = ingest(args.workdir, args.archive_dir, args.only)
    print(f"Fontes validadas: {len(manifest['sources'])}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
