"""Aggregate ELT electorate CSV into the three existing Power BI schemas.

The output is local staging only. It never creates a live batch manifest.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pandas as pd

METRICS = ['QT_ELEITORES', 'QT_ELEITORES_BIOMETRIA', 'QT_ELEITORES_DEFICIENCIA', 'QT_ELEITORES_NOME_SOCIAL']
BASE = ['DT_GERACAO', 'HH_GERACAO', 'AA_ELEICAO', 'SG_UF', 'CD_MUNICIPIO', 'NM_MUNICIPIO']
DIMENSIONS = [('GENERO', 'CD_GENERO', 'DS_GENERO'), ('ESTADO_CIVIL', 'CD_ESTADO_CIVIL', 'DS_ESTADO_CIVIL'),
              ('FAIXA_ETARIA', 'CD_FAIXA_ETARIA', 'DS_FAIXA_ETARIA'), ('ESCOLARIDADE', 'CD_GRAU_ESCOLARIDADE', 'DS_GRAU_ESCOLARIDADE'),
              ('RACA_COR', 'CD_RACA_COR', 'DS_RACA_COR'), ('IDENTIDADE_GENERO', 'CD_IDENTIDADE_GENERO', 'DS_IDENTIDADE_GENERO'),
              ('QUILOMBOLA', 'CD_QUILOMBOLA', 'DS_QUILOMBOLA'), ('INTERPRETE_LIBRAS', 'CD_INTERPRETE_LIBRAS', 'DS_INTERPRETE_LIBRAS')]
LOCATION = BASE + ['NR_ZONA']
PROFILE = BASE[:4] + [column for _, code, description in DIMENSIONS for column in (code, description)]
MUNICIPAL = BASE + ['DIMENSAO', 'CD_CATEGORIA', 'DS_CATEGORIA']


def aggregate(frame, keys):
    return frame.groupby(keys, dropna=False, sort=False, as_index=False)[METRICS].sum()


def merge(current, piece, keys):
    return piece if current is None else aggregate(pd.concat([current, piece], ignore_index=True), keys)


def prepare(source: Path, reference: Path, output: Path, chunksize=150_000):
    if output.exists():
        raise FileExistsError(output)
    schemas = json.loads(reference.read_text(encoding='utf-8-sig'))['datasets']
    expected = {'Eleitorado_Localidade': LOCATION + METRICS,
                'eleitorado_cruzado': PROFILE + METRICS,
                'eleitorado_municipio': MUNICIPAL + METRICS}
    for name, columns in expected.items():
        if schemas[name]['columns'] != columns:
            raise ValueError(f'Reference schema mismatch: {name}')
    header = pd.read_csv(source, sep=';', encoding='utf-8-sig', nrows=0).columns.tolist()
    required = set(LOCATION + PROFILE + METRICS)
    if not required.issubset(header):
        raise ValueError('Missing source columns: ' + ', '.join(sorted(required - set(header))))
    totals = {metric: 0 for metric in METRICS}
    results = {name: None for name in expected}
    count = 0
    for chunk in pd.read_csv(source, sep=';', encoding='utf-8-sig', dtype=str,
                             keep_default_na=False, chunksize=chunksize, on_bad_lines='error'):
        count += len(chunk)
        for metric in METRICS:
            # Same semantics as the original report's electorate optimizer.
            chunk[metric] = pd.to_numeric(chunk[metric], errors='coerce').fillna(0).clip(lower=0).astype('int64')
            totals[metric] += int(chunk[metric].sum())
        results['Eleitorado_Localidade'] = merge(results['Eleitorado_Localidade'], aggregate(chunk, LOCATION), LOCATION)
        results['eleitorado_cruzado'] = merge(results['eleitorado_cruzado'], aggregate(chunk, PROFILE), PROFILE)
        pieces = []
        for dimension, code, description in DIMENSIONS:
            piece = aggregate(chunk, BASE + [code, description]).rename(columns={code: 'CD_CATEGORIA', description: 'DS_CATEGORIA'})
            piece['DIMENSAO'] = dimension
            pieces.append(piece[MUNICIPAL + METRICS])
        results['eleitorado_municipio'] = merge(results['eleitorado_municipio'], pd.concat(pieces, ignore_index=True), MUNICIPAL)
    if not count:
        raise ValueError('Empty source')
    for name in ('Eleitorado_Localidade', 'eleitorado_cruzado'):
        if any(int(results[name][metric].sum()) != totals[metric] for metric in METRICS):
            raise ValueError(f'Aggregate totals mismatch: {name}')
    for dimension, _, _ in DIMENSIONS:
        subset = results['eleitorado_municipio'].query('DIMENSAO == @dimension')
        if any(int(subset[metric].sum()) != totals[metric] for metric in METRICS):
            raise ValueError(f'Municipal totals mismatch: {dimension}')
    output.mkdir(parents=True, exist_ok=False)
    for name, columns in expected.items():
        results[name][columns].to_csv(output / f'{name}.csv', sep=';', index=False, encoding='utf-8-sig')
    audit = {'status': 'incomplete', 'publication_allowed': False, 'source_rows': count,
             'source_totals': totals, 'rows': {name: len(frame) for name, frame in results.items()}}
    (output / 'electorate-audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    return audit


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    print(json.dumps(prepare(arguments.source, arguments.reference, arguments.output), ensure_ascii=False))
