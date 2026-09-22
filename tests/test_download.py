import zipfile
from pathlib import Path

import pytest

from pipeline.download import MEMBER, extract_verified


def test_extract_verified(tmp_path: Path):
    archive = tmp_path / "source.zip"
    content = b'"ANO_ELEICAO";"SQ_CANDIDATO";"SG_UF";"DS_CARGO"\n' + b'2026;1;DF;SENADOR\n' * 1000
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(MEMBER, content)
    output = tmp_path / MEMBER
    result = extract_verified(archive, output)
    assert output.read_bytes() == content
    assert result["raw_bytes"] == len(content)


def test_rejects_missing_member(tmp_path: Path):
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("wrong.csv", b"x" * 20_000)
    with pytest.raises(ValueError):
        extract_verified(archive, tmp_path / MEMBER)
