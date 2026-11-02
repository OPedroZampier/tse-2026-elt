import hashlib
import json
import pytest
from powerbi_results import advances_to_runoff, integer, load_documents, validate_coverage


def make_audit(work, file, election, turn, uf, content_override=None):
    data = {'ele': str(election), 't': str(turn), 'cdabr': uf, 'f': 'o', 'carg': [{'cd': '1'}]}
    content = json.dumps(data).encode()
    cache = work / 'results-json'
    cache.mkdir(exist_ok=True)
    filename = f'{uf.lower()}-c0001-e{election:06d}-u.json'
    (cache / filename).write_bytes(content_override if content_override is not None else content)
    audit = {'reconciliation_passed': True, 'expected_documents': 1,
             'sources': [{'url': f'https://resultados.tse.jus.br/{filename}',
                          'sha256': hashlib.sha256(content).hexdigest()}]}
    (work / file).write_text(json.dumps(audit), encoding='utf8')


def test_checks_both_round_manifests_and_hashes(tmp_path):
    make_audit(tmp_path, 'results-sources.json', 6257, 1, 'AC')
    make_audit(tmp_path, 'runoff-sources.json', 6258, 2, 'AC')
    assert len(load_documents(tmp_path)) == 2
    (tmp_path / 'results-json' / 'ac-c0001-e006258-u.json').write_text('{}', encoding='utf8')
    with pytest.raises(ValueError, match='digest mismatch'):
        load_documents(tmp_path)


def test_rejects_unreconciled_manifest(tmp_path):
    make_audit(tmp_path, 'results-sources.json', 6257, 1, 'AC')
    path = tmp_path / 'results-sources.json'
    audit = json.loads(path.read_text())
    audit['reconciliation_passed'] = False
    path.write_text(json.dumps(audit))
    with pytest.raises(ValueError, match='Incomplete source audit'):
        load_documents(tmp_path)


def test_integer_parsing():
    assert integer('7') == 7
    assert integer('') == 0
    with pytest.raises(ValueError):
        integer('not-a-number')


def test_runoff_status_uses_first_round_label():
    assert advances_to_runoff('2º turno') == 1
    assert advances_to_runoff('ELEITO') == 0
    assert advances_to_runoff('NÃO ELEITO') == 0


def test_missing_state_documents_cannot_pass():
    with pytest.raises(ValueError, match='Incomplete first-round'):
        validate_coverage([])
