import csv
import hashlib
import json
import pytest
import verify_assembled_staging as verifier


def test_detects_tampering_and_keeps_batch_nonpublishable(tmp_path, monkeypatch):
    monkeypatch.setattr(verifier, 'DIRECT', {'Candidatos': 'unused'})
    monkeypatch.setattr(verifier, 'ELECTORATE', ())
    monkeypatch.setattr(verifier, 'RESULTS', ())
    root = tmp_path / 'batch'
    folder = root / 'Candidatos'
    folder.mkdir(parents=True)
    path = folder / 'part-00001.csv'
    with path.open('w', encoding='utf-8-sig', newline='') as file:
        writer = csv.writer(file, delimiter=';')
        writer.writerow(['NOME', 'CPF'])
        writer.writerow(['Nome', ''])
    dataset = {'columns': ['NOME', 'CPF'], 'encoding': 65001, 'rows': 1,
               'files': [{'name': path.name, 'bytes': path.stat().st_size,
                          'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'rows': 1}]}
    (root / 'assembly-audit.json').write_text(json.dumps({'status': 'incomplete',
        'publication_allowed': False, 'datasets': {'Candidatos': dataset}}))
    reference = tmp_path / 'reference.json'
    reference.write_text(json.dumps({'datasets': {'Candidatos': {'columns': dataset['columns']}}}))
    checked = verifier.verify(root, reference)
    assert checked['local_integrity_verified'] and not checked['publication_allowed']
    path.write_text('changed', encoding='utf8')
    with pytest.raises(ValueError, match='size or hash'):
        verifier.verify(root, reference)
