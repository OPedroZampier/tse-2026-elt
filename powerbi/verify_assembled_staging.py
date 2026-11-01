"""Independently verify local staging without making it publishable."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from powerbi_direct_sources import DIRECT
from powerbi_assemble_staging import ELECTORATE, RESULTS
from prepare_powerbi_cloud_batch import sensitive


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as file:
        while chunk := file.read(1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def verify(root: Path, reference: Path):
    audit = json.loads((root / 'assembly-audit.json').read_text(encoding='utf-8'))
    ref = json.loads(reference.read_text(encoding='utf-8-sig'))['datasets']
    expected = set(DIRECT) | set(ELECTORATE) | set(RESULTS)
    if audit['status'] != 'incomplete' or audit['publication_allowed'] or set(audit['datasets']) != expected:
        raise ValueError('Unsafe status or missing datasets')
    if (root / 'manifest.json').exists():
        raise ValueError('Live manifest unexpectedly present')
    expected_files = set()
    rows_total, parts_total = 0, 0
    metrics = {'electorate': 0, 'first_round_president_votes': 0, 'second_round_president_votes': 0}
    for name, dataset in audit['datasets'].items():
        if dataset['columns'] != ref[name]['columns'] or not dataset['files']:
            raise ValueError(f'Unexpected schema or no parts: {name}')
        redacted = [i for i, column in enumerate(dataset['columns']) if sensitive(column)]
        dataset_rows = 0
        for index, part in enumerate(dataset['files'], 1):
            if part['name'] != f'part-{index:05d}.csv':
                raise ValueError(f'Invalid part sequence: {name}')
            path = root / name / part['name']
            expected_files.add(path)
            if path.stat().st_size != part['bytes'] or part['bytes'] > 40_000_000 or digest(path) != part['sha256']:
                raise ValueError(f'Invalid part size or hash: {name}')
            count = 0
            encoding = {65001: 'utf-8-sig', 1252: 'latin-1'}[dataset['encoding']]
            with path.open(encoding=encoding, newline='') as file:
                reader = csv.reader(file, delimiter=';')
                if next(reader) != dataset['columns']:
                    raise ValueError(f'Header mismatch: {name}')
                for row in reader:
                    if len(row) != len(dataset['columns']) or any(row[i] for i in redacted):
                        raise ValueError(f'Bad record or retained identifier: {name}')
                    if name == 'Eleitorado_Localidade':
                        metrics['electorate'] += int(row[dataset['columns'].index('QT_ELEITORES')])
                    elif name == 'PT_Controle':
                        entry = dict(zip(dataset['columns'], row))
                        if entry['uf'] == 'BR':
                            raise ValueError('Duplicate national control row in published facts')
                        if int(entry['codigo_cargo']) == 1:
                            if entry['turno'] not in ('1', '2'):
                                raise ValueError('Unexpected election round')
                            label = 'first_round_president_votes' if entry['turno'] == '1' else 'second_round_president_votes'
                            metrics[label] += int(entry['votos_validos'])
                    count += 1
            if count != part['rows']:
                raise ValueError(f'Part row count mismatch: {name}')
            dataset_rows += count
            parts_total += 1
        if dataset_rows != dataset['rows']:
            raise ValueError(f'Dataset row count mismatch: {name}')
        rows_total += dataset_rows
    if set(root.rglob('*.csv')) != expected_files:
        raise ValueError('Unlisted or missing CSV file')
    return {'local_integrity_verified': True, 'datasets': len(expected), 'parts': parts_total,
            'rows': rows_total, 'metrics': metrics, 'cloud_verified': False,
            'publication_allowed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.root, args.reference), indent=2))
