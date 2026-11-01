import json
import pytest
import csv
import hashlib
import powerbi_assemble_staging as assembly
from powerbi_assemble_staging import DIRECT, ELECTORATE, RESULTS, assemble
from powerbi_direct_sources import prepare


def test_rejects_mixed_candidate_snapshots_before_writing(tmp_path):
    reference = tmp_path / 'reference.json'
    reference.write_text(json.dumps({'status': 'ready', 'datasets': {name: {} for name in (*DIRECT, *ELECTORATE, *RESULTS)}}))
    direct, electorate, results = [tmp_path / name for name in ('direct', 'electorate', 'results')]
    for path in (direct, electorate, results):
        path.mkdir()
    audit = {'status': 'incomplete', 'publication_allowed': False}
    (direct / 'direct-sources-audit.json').write_text(json.dumps({**audit, 'datasets': {
        name: ({'source_sha256': 'first'} if name == 'Candidatos' else {}) for name in DIRECT}}))
    (electorate / 'electorate-audit.json').write_text(json.dumps(audit))
    (results / 'results-audit.json').write_text(json.dumps({**audit, 'candidate_source_sha256': 'second'}))
    output = tmp_path / 'assembled'
    with pytest.raises(ValueError, match='Candidate source differs'):
        assemble(reference, direct, electorate, results, output)
    assert not output.exists()


def test_local_assembly_validates_and_blocks_stale_candidate_data(tmp_path, monkeypatch):
    monkeypatch.setattr(assembly, 'DIRECT', {'Candidatos': 'input.csv'})
    monkeypatch.setattr(assembly, 'ELECTORATE', ())
    monkeypatch.setattr(assembly, 'RESULTS', ())
    batch_id = '20261030T002338Z'
    schema = ['DT_GERACAO', 'NR_CPF_CANDIDATO']
    baseline_dir = tmp_path / 'batches' / batch_id / 'Candidatos'
    baseline_dir.mkdir(parents=True)
    baseline = baseline_dir / 'part-00001.csv'
    with baseline.open('w', encoding='utf-8-sig', newline='') as file:
        writer = csv.writer(file, delimiter=';')
        writer.writerow(schema)
        writer.writerow(['05/10/2026', ''])
    reference = tmp_path / 'reference.json'
    reference.write_text(json.dumps({'status': 'ready', 'batch_id': batch_id, 'datasets': {'Candidatos': {
        'columns': schema, 'encoding': 65001, 'files': [{'name': baseline.name}]}}}))
    raw = tmp_path / 'raw'
    raw.mkdir()
    source = raw / 'input.csv'
    def write_source(date):
        with source.open('w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file, delimiter=';')
            writer.writerow(schema)
            writer.writerow([date, '12345678900'])
    electorate = tmp_path / 'electorate'
    results = tmp_path / 'results'
    electorate.mkdir()
    results.mkdir()
    (electorate / 'electorate-audit.json').write_text(json.dumps({'status': 'incomplete', 'publication_allowed': False}))
    write_source('04/10/2026')
    stale = tmp_path / 'stale'
    stale_audit = prepare(raw, reference, stale, {'Candidatos': 'input.csv'})
    (results / 'results-audit.json').write_text(json.dumps({'status': 'incomplete', 'publication_allowed': False,
        'candidate_source_sha256': stale_audit['datasets']['Candidatos']['source_sha256']}))
    with pytest.raises(ValueError, match='older than'):
        assemble(reference, stale, electorate, results, tmp_path / 'stale-out')
    assert not (tmp_path / 'stale-out').exists()
    write_source('31/10/2026')
    current = tmp_path / 'current'
    current_audit = prepare(raw, reference, current, {'Candidatos': 'input.csv'})
    (results / 'results-audit.json').write_text(json.dumps({'status': 'incomplete', 'publication_allowed': False,
        'candidate_source_sha256': current_audit['datasets']['Candidatos']['source_sha256']}))
    output = tmp_path / 'assembled'
    result = assemble(reference, current, electorate, results, output)
    assert not result['publication_allowed']
    assert not (output / 'manifest.json').exists()
    assert (output / 'Candidatos' / 'part-00001.csv').exists()
    # A CI runner may download the deployed baseline outside the original layout.
    ref = json.loads(reference.read_text())
    ref['datasets']['Candidatos']['files'][0].update(bytes=baseline.stat().st_size,
        sha256=hashlib.sha256(baseline.read_bytes()).hexdigest())
    reference.write_text(json.dumps(ref))
    external = tmp_path / 'downloaded.csv'
    external.write_bytes(baseline.read_bytes())
    assemble(reference, current, electorate, results, tmp_path / 'external-out', external)
    external.write_bytes(b'changed')
    with pytest.raises(ValueError, match='does not match'):
        assemble(reference, current, electorate, results, tmp_path / 'bad-out', external)
    assert not (tmp_path / 'bad-out').exists()
    ref['status'] = 'incomplete'
    reference.write_text(json.dumps(ref))
    with pytest.raises(ValueError, match='not marked ready'):
        assemble(reference, current, electorate, results, tmp_path / 'unready-out', baseline)
    assert not (tmp_path / 'unready-out').exists()
