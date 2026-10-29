"""Collect official second-round results, excluding duplicate BR aggregates."""
from __future__ import annotations
import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from pipeline.results import UFS, fetch, parse, reconcile_brazil, verify_document, write_csv


def runoff_states(cache: Path) -> list[str]:
    states = []
    for uf in UFS:
        data = json.loads((cache / f'{uf.lower()}-c0003-e006259-u.json').read_text(encoding='utf-8'))
        verify_document(data, (uf, 6259, 3))
        if data['tf'] != 's':
            raise ValueError(f'First round not finalized: {uf}')
        statuses = [c['st'].lower() for a in data['carg'][0]['agr']
                    for p in a['par'] for c in p.get('cand', [])]
        advancing = [s for s in statuses if s.startswith('2') and 'turno' in s]
        if advancing:
            if len(advancing) != 2:
                raise ValueError(f'Unexpected runoff candidate count: {uf}')
            states.append(uf)
    return states


def collect(workdir: Path):
    cache = workdir / 'results-json'
    states = runoff_states(cache)
    tasks = [('BR', 6258, 1)] + [(uf, 6258, 1) for uf in UFS + ['ZZ']]
    tasks += [(uf, 6260, 3) for uf in states]
    with ThreadPoolExecutor(max_workers=4) as pool:
        documents = list(pool.map(lambda task: fetch(task, cache), tasks))
    facts, candidates, parties = [], [], []
    for task, data, _ in documents:
        fact, cand, party, quotient = parse(task, data)
        if data['tf'] != 's' or fact['secoes_totalizadas'] != fact['secoes_total']:
            raise ValueError(f'Runoff not fully counted: {task}')
        if quotient is not None:
            raise ValueError('Proportional quota cannot apply to a runoff')
        facts.append(fact)
        if task[0] != 'BR':
            candidates.extend(cand)
            parties.extend(party)
    reconcile_brazil(facts)
    tables = {'abrangencia': [r for r in facts if r['uf'] != 'BR'],
              'candidatos': candidates, 'partidos': parties}
    for label, rows, keys in (
        ('abrangencia', tables['abrangencia'], ('chave_resultado',)),
        ('candidatos', candidates, ('chave_resultado', 'id_candidato')),
        ('partidos', parties, ('chave_resultado', 'numero_partido')),
    ):
        if len(rows) != len({tuple(r[k] for k in keys) for r in rows}):
            raise ValueError(f'Duplicate runoff keys: {label}')
    folder = workdir / 'raw' / 'resultados_segundo_turno'
    folder.mkdir(parents=True, exist_ok=True)
    for name, rows in tables.items():
        write_csv(folder / f'{name}.csv', rows)
    manifest = dict(extracted_at_utc=datetime.now(timezone.utc).isoformat(), turno=2,
                    expected_documents=len(tasks), downloaded_documents=len(documents),
                    reconciliation_passed=True, national_rows_published=False,
                    governor_runoff_states=states,
                    rows={name: len(rows) for name, rows in tables.items()},
                    sources=[source for _, _, source in documents])
    (workdir / 'runoff-sources.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in manifest.items() if k != 'sources'}))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workdir', type=Path, default=Path('work'))
    collect(parser.parse_args().workdir)
