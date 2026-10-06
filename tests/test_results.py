import copy
import pytest
from pipeline.results import UFS, parse, reconcile_brazil, tasks, verify_document

def document(uf='BR'):
    return dict(f='o', ele='6257', t='1', cdabr=uf.lower(), dg='05/10/2026', hg='12:00:00', tf='s',
                s=dict(ts='1', st='1'), e=dict(te='10', esa='10', c='8', a='2'),
                v=dict(tv='8', vv='6', vnom='6', vl='0', vb='1', tvn='1', van='0', vansj='0'),
                carg=[dict(cd='1', agr=[])])

def test_exact_coverage_and_df_office():
    assert len(tasks()) == len(set(tasks())) == 137
    assert ('ZZ', 6257, 1) in tasks()
    assert ('DF', 6259, 8) in tasks()
    assert ('DF', 6259, 7) not in tasks()

@pytest.mark.parametrize('field,value', [('t', '2'), ('f', 's'), ('ele', '6259'), ('cdabr', 'sp')])
def test_wrong_document_rejected(field, value):
    data = document()
    data[field] = value
    with pytest.raises(ValueError):
        verify_document(data, ('BR', 6257, 1))

def test_votes_and_attendance_reconciled():
    data = document()
    assert parse(('BR', 6257, 1), data)[0]['votos_validos'] == 6
    data['e']['a'] = '3'
    with pytest.raises(ValueError, match='Attendance'):
        parse(('BR', 6257, 1), data)

def test_invalid_vote_counts_rejected():
    data = document()
    data['v']['vnom'] = '5'
    with pytest.raises(ValueError, match='Valid-vote'):
        parse(('BR', 6257, 1), data)

def test_majoritarian_party_has_no_legend_field():
    data = document()
    data['carg'][0]['agr'] = [dict(par=[dict(n='13', sg='PT', tvtn='6', tvan='0')])]
    assert parse(('BR', 6257, 1), data)[2][0]['votos_legenda'] == 0

def test_national_reconciliation_includes_abroad():
    local = [parse((uf, 6257, 1), document(uf))[0] for uf in UFS + ['ZZ']]
    total = copy.deepcopy(local[0])
    total['uf'] = 'BR'
    for column in ('comparecimento', 'abstencoes', 'votos_total', 'votos_validos',
                   'votos_nominais', 'votos_brancos', 'votos_nulos_total', 'secoes_totalizadas'):
        total[column] = sum(row[column] for row in local)
    reconcile_brazil([total] + local)
    with pytest.raises(ValueError, match='coverage'):
        reconcile_brazil([total] + local[:-1])
    total['votos_validos'] += 1
    with pytest.raises(ValueError, match='BR !='):
        reconcile_brazil([total] + local)
