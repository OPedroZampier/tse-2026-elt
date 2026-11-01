"""Combine verified source families into a local, non-publishable staging batch."""
from __future__ import annotations
import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil

from prepare_powerbi_cloud_batch import split_csv
from powerbi_direct_sources import DIRECT

ELECTORATE = ('Eleitorado_Localidade', 'eleitorado_cruzado', 'eleitorado_municipio')
RESULTS = ('PT_Controle', 'PT_Votos', 'PT_Partidos', 'PT_QE', 'PT_Cadastro')


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def candidate_date(path, encoding='utf-8-sig'):
    with path.open(encoding=encoding, newline='') as file:
        row = next(csv.DictReader(file, delimiter=';'))
    return datetime.strptime(row['DT_GERACAO'], '%d/%m/%Y').date()


def assemble(reference: Path, direct: Path, electorate: Path, results: Path, output: Path, baseline_candidate: Path | None = None):
    if output.exists():
        raise FileExistsError(output)
    ref = json.loads(reference.read_text(encoding='utf-8-sig'))
    if ref.get('status') != 'ready':
        raise ValueError('Reference manifest is not marked ready')
    direct_audit = json.loads((direct / 'direct-sources-audit.json').read_text(encoding='utf-8'))
    elect_audit = json.loads((electorate / 'electorate-audit.json').read_text(encoding='utf-8'))
    results_audit = json.loads((results / 'results-audit.json').read_text(encoding='utf-8'))
    if any(x['publication_allowed'] or x['status'] != 'incomplete' for x in (direct_audit, elect_audit, results_audit)):
        raise ValueError('Unexpected input staging status')
    if set(direct_audit['datasets']) != set(DIRECT) or set(ref['datasets']) != set(DIRECT) | set(ELECTORATE) | set(RESULTS):
        raise ValueError('Incomplete dataset contract')
    if direct_audit['datasets']['Candidatos'].get('source_sha256') != results_audit.get('candidate_source_sha256') or not results_audit.get('candidate_source_sha256'):
        raise ValueError('Candidate source differs between direct and results inputs')
    for name, item in direct_audit['datasets'].items():
        if item['columns'] != ref['datasets'][name]['columns'] or not item['files']:
            raise ValueError(f'Invalid direct source contract: {name}')
        for part in item['files']:
            path = direct / name / part['name']
            if path.stat().st_size != part['bytes'] or sha256(path) != part['sha256']:
                raise ValueError(f'Direct source verification failed: {name}')
    baseline = baseline_candidate or (reference.parent / 'batches' / ref['batch_id'] / 'Candidatos' / ref['datasets']['Candidatos']['files'][0]['name'])
    baseline_info = ref['datasets']['Candidatos']['files'][0]
    if baseline_candidate is not None:
        if baseline.stat().st_size != baseline_info['bytes'] or sha256(baseline) != baseline_info['sha256']:
            raise ValueError('Candidate baseline does not match the deployed manifest')
    original_encoding = 'utf-8-sig' if ref['datasets']['Candidatos']['encoding'] == 65001 else 'latin-1'
    if candidate_date(direct / 'Candidatos' / direct_audit['datasets']['Candidatos']['files'][0]['name']) < candidate_date(baseline, original_encoding):
        raise ValueError('Candidate source is older than the deployed snapshot')
    input_hashes = {}
    for name in ELECTORATE + RESULTS:
        root = electorate if name in ELECTORATE else results
        audit = elect_audit if name in ELECTORATE else results_audit
        source_path = root / f'{name}.csv'
        input_hashes[name] = sha256(source_path)
        with source_path.open(encoding='utf-8-sig', newline='') as file:
            reader = csv.reader(file, delimiter=';')
            if next(reader, None) != ref['datasets'][name]['columns']:
                raise ValueError(f'Unexpected schema: {name}')
            count = sum(1 for _ in reader)
        if count != audit['rows'][name] or count == 0:
            raise ValueError(f'Unexpected row count: {name}')
        if sha256(source_path) != input_hashes[name]:
            raise ValueError(f'Source changed during validation: {name}')
    output.mkdir(parents=True, exist_ok=False)
    datasets = {}
    for name, item in direct_audit['datasets'].items():
        destination = output / name
        destination.mkdir()
        for part in item['files']:
            shutil.copyfile(direct / name / part['name'], destination / part['name'])
            if sha256(destination / part['name']) != part['sha256']:
                raise ValueError(f'Copied part differs: {name}')
        datasets[name] = item
    for name in ELECTORATE + RESULTS:
        root = electorate if name in ELECTORATE else results
        with (root / f'{name}.csv').open(encoding='utf-8-sig', newline='') as source:
            datasets[name] = split_csv(source, output / name)
        if sha256(root / f'{name}.csv') != input_hashes[name]:
            raise ValueError(f'Source changed during assembly: {name}')
    audit = {'status': 'incomplete', 'publication_allowed': False, 'datasets': datasets,
             'reason': 'Local staging only; independent verification and production integration remain.'}
    (output / 'assembly-audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    return audit


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('reference', 'direct', 'electorate', 'results', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--baseline-candidate', type=Path, help='Verified first candidate part from the deployed batch')
    args = parser.parse_args()
    result = assemble(args.reference, args.direct, args.electorate, args.results, args.output, args.baseline_candidate)
    print(f"Staged {len(result['datasets'])} datasets; publication is disabled.")
