import copy
import json
import pytest
from pipeline.results import parse, verify_document, UFS
from pipeline.runoff import runoff_states
from tests.test_results import document


def test_second_round_identity_and_no_quota():
    data = document('ZZ')
    data.update(ele='6258', t='2')
    fact, _, _, quota = parse(('ZZ', 6258, 1), data)
    assert fact['turno'] == 2
    assert fact['chave_resultado'] == '6258-2-ZZ-1'
    assert quota is None
    data['t'] = '1'
    with pytest.raises(ValueError):
        verify_document(data, ('ZZ', 6258, 1))


def test_governor_coverage_comes_from_first_round(tmp_path):
    for uf in UFS:
        data = document(uf)
        data['ele'] = '6259'
        data['carg'][0]['cd'] = '3'
        statuses = ['2º turno', '2º turno'] if uf == 'AC' else ['Eleito', 'Não eleito']
        data['carg'][0]['agr'] = [{'par': [{'cand': [{'st': s} for s in statuses]}]}]
        (tmp_path / f'{uf.lower()}-c0003-e006259-u.json').write_text(json.dumps(data), encoding='utf-8')
    assert runoff_states(tmp_path) == ['AC']
    data['tf'] = 'n'
    (tmp_path / 'to-c0003-e006259-u.json').write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError, match='not finalized'):
        runoff_states(tmp_path)
