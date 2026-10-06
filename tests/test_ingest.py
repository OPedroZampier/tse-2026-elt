import zipfile
from pathlib import Path

import pytest

from pipeline.ingest import extract, ingest
from pipeline import ingest as ingest_module
from pipeline.sources import Source


def test_extract_selects_expected_national_csv(tmp_path: Path):
    source = Source("example", "example.zip", ("data_BRASIL.csv",), ("SQ_CANDIDATO",))
    archive_path = tmp_path / "example.zip"
    content = '"SQ_CANDIDATO";"NOME"\n1;"João"\n'.encode("latin-1")
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("nested/data_BRASIL.csv", content + b"2;Maria\n" * 20)
        archive.writestr("data_SP.csv", b"wrong" * 100)

    result = extract(source, archive_path, tmp_path / "raw")
    output = tmp_path / "raw" / "example" / "data_BRASIL.csv"
    assert output.read_text(encoding="utf-8").startswith('"SQ_CANDIDATO";"NOME"\n1;"João"')
    assert result["files"][0]["physical_data_lines"] == 21


def test_extract_rejects_missing_expected_member(tmp_path: Path):
    source = Source("example", "example.zip", ("data_BRASIL.csv",), ("SQ_CANDIDATO",))
    archive_path = tmp_path / "example.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("data_SP.csv", b"wrong" * 100)

    with pytest.raises(ValueError, match="esperado data_BRASIL.csv"):
        extract(source, archive_path, tmp_path / "raw")


def test_extract_rejects_header_change(tmp_path: Path):
    source = Source("example", "example.zip", ("data_BRASIL.csv",), ("SQ_CANDIDATO",))
    archive_path = tmp_path / "example.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("data_BRASIL.csv", b"WRONG;NAME\n" + b"1;Maria\n" * 20)

    with pytest.raises(ValueError, match="cabeçalho inesperado"):
        extract(source, archive_path, tmp_path / "raw")


def test_refresh_downloads_cached_zip_but_preserves_explicit_offline_archive(tmp_path, monkeypatch):
    source = Source("example", "example.zip", ("data.csv",), ("ID",))
    monkeypatch.setitem(ingest_module.BY_KEY, 'example', source)
    downloads = []
    monkeypatch.setattr(ingest_module, 'fetch', lambda source, path: downloads.append(path))
    monkeypatch.setattr(ingest_module, 'extract', lambda *args: {'source': 'example', 'files': []})
    cached = tmp_path / 'zips' / source.archive_name
    cached.parent.mkdir()
    cached.touch()
    ingest(tmp_path, keys=['example'], refresh=True)
    assert downloads == [cached]
    supplied = tmp_path / 'offline'
    supplied.mkdir()
    (supplied / source.archive_name).touch()
    downloads.clear()
    ingest(tmp_path, archive_dir=supplied, keys=['example'], refresh=True)
    assert downloads == []
