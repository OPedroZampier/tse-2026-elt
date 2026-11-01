import csv
import json

import pytest

from powerbi_direct_sources import prepare


def fixture_inputs(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    path = raw / "input.csv"
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(["NOME", "NR_CPF_CANDIDATO"])
        writer.writerow(["Pessoa", "12345678900"])
    ref = tmp_path / "reference.json"
    ref.write_text(json.dumps({"datasets": {"Candidatos": {"columns": ["NOME", "NR_CPF_CANDIDATO"]}}}), encoding="utf-8")
    return raw, ref


def test_prepares_redacted_non_publishable_batch(tmp_path):
    raw, reference = fixture_inputs(tmp_path)
    output = tmp_path / "batch"
    result = prepare(raw, reference, output, {"Candidatos": "input.csv"})
    assert not result["publication_allowed"]
    assert result["status"] == "incomplete"
    assert not (output / "manifest.json").exists()
    with (output / "Candidatos" / "part-00001.csv").open(encoding="utf-8-sig", newline="") as file:
        assert list(csv.reader(file, delimiter=";")) == [["NOME", "NR_CPF_CANDIDATO"], ["Pessoa", ""]]


def test_schema_error_does_not_create_output(tmp_path):
    raw, reference = fixture_inputs(tmp_path)
    reference.write_text(json.dumps({"datasets": {"Candidatos": {"columns": ["OUTRA"]}}}), encoding="utf-8")
    output = tmp_path / "batch"
    with pytest.raises(ValueError, match="schema differs"):
        prepare(raw, reference, output, {"Candidatos": "input.csv"})
    assert not output.exists()


def test_existing_destination_is_never_overwritten(tmp_path):
    raw, reference = fixture_inputs(tmp_path)
    output = tmp_path / "batch"
    output.mkdir()
    marker = output / "keep.txt"
    marker.write_text("preserve", encoding="utf-8")
    with pytest.raises(FileExistsError):
        prepare(raw, reference, output, {"Candidatos": "input.csv"})
    assert marker.read_text(encoding="utf-8") == "preserve"
