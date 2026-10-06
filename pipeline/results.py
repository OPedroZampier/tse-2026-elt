"""Download and reconcile official first-round results before dbt ingestion."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

UFS = 'AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO'.split()
CARGOS = {1: 'Presidente', 3: 'Governador', 5: 'Senador', 6: 'Deputado Federal', 7: 'Deputado Estadual', 8: 'Deputado Distrital'}
URL = 'https://resultados.tse.jus.br/oficial/ele2026/{ele}/dados/{uf}/{uf}-c{cargo:04d}-e{ele:06d}-u.json'


def tasks():
    return [('BR', 6257, 1)] + [(uf, 6257, 1) for uf in UFS + ['ZZ']] + [
        (uf, 6259, cargo) for uf in UFS for cargo in (3, 5, 6, 8 if uf == 'DF' else 7)
    ]


def verify_document(data, task):
    uf, election, cargo = task
    if (data.get('f') != 'o' or int(data['ele']) != election or int(data['t']) != 1
            or data['cdabr'].upper() != uf or len(data['carg']) != 1
            or int(data['carg'][0]['cd']) != cargo):
        raise ValueError(f'Unexpected election/turn/territory/office: {task}')


def fetch(task, cache):
    uf, election, cargo = task
    url = URL.format(uf=uf.lower(), ele=election, cargo=cargo)
    path = cache / f'{uf.lower()}-c{cargo:04d}-e{election:06d}-u.json'
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'TSE-2026-ELT/1.0'})
            with urllib.request.urlopen(req, timeout=60) as response:
                raw = response.read()
            data = json.loads(raw)
            verify_document(data, task)
            path.write_bytes(raw)
            return task, data, dict(url=url, sha256=hashlib.sha256(raw).hexdigest(),
                                   generated_at_tse=data['dg'] + ' ' + data['hg'])
        except Exception:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def parse(task, data):
    verify_document(data, task)
    uf, election, office = task
    key = f'{election}-1-{uf}-{office}'
    common = dict(chave_resultado=key, ano_eleicao=2026, eleicao=election, turno=1,
                  uf=uf, codigo_cargo=office, cargo=CARGOS[office],
                  data_geracao=data['dg'], hora_geracao=data['hg'])
    s, e, v = data['s'], data['e'], data['v']
    fact = dict(common, totalizacao_finalizada=data['tf'], secoes_total=int(s['ts']),
                secoes_totalizadas=int(s['st']), eleitorado=int(e['te']),
                eleitores_secoes_apuradas=int(e['esa']), comparecimento=int(e['c']),
                abstencoes=int(e['a']), votos_total=int(v['tv']), votos_validos=int(v['vv']),
                votos_nominais=int(v['vnom']), votos_legenda=int(v.get('vl', '0')),
                votos_brancos=int(v['vb']), votos_nulos_total=int(v['tvn']),
                votos_anulados=int(v['van']), votos_anulados_sub_judice=int(v['vansj']))
    if fact['comparecimento'] + fact['abstencoes'] != fact['eleitores_secoes_apuradas']:
        raise ValueError(f'Attendance reconciliation failed: {key}')
    if fact['votos_validos'] != fact['votos_nominais'] + fact['votos_legenda']:
        raise ValueError(f'Valid-vote reconciliation failed: {key}')
    if fact['votos_total'] != sum(fact[c] for c in ('votos_validos', 'votos_brancos',
            'votos_nulos_total', 'votos_anulados', 'votos_anulados_sub_judice')):
        raise ValueError(f'Total-vote reconciliation failed: {key}')
    if not 0 <= fact['secoes_totalizadas'] <= fact['secoes_total']:
        raise ValueError(f'Invalid section counts: {key}')
    candidates, parties = [], []
    for group in data['carg'][0]['agr']:
        for party in group['par']:
            parties.append(dict(common, numero_partido=party['n'], partido=party['sg'],
                votos_nominais=int(party['tvtn']),
                votos_legenda=int(party['tvtl']) if office in (6, 7, 8) else 0,
                votos_anulados=int(party['tvan'])))
            for candidate in party.get('cand', []):
                candidates.append(dict(common, id_candidato=candidate['sqcand'],
                    numero_candidato=candidate['n'], nome_urna=candidate['nmu'],
                    partido=party['sg'], resultado=candidate['st'],
                    destino_votos=candidate['dvt'], votos=int(candidate['vap']),
                    percentual_oficial=float(candidate['pvapn'].replace(',', '.')) / 100))
    quotient = None
    if office in (6, 7, 8):
        quotient = dict(common, quociente_eleitoral=int(data['carg'][0]['qe']),
                        vagas=int(data['carg'][0]['nv']))
    return fact, candidates, parties, quotient


def reconcile_brazil(facts):
    control = next(row for row in facts if row['uf'] == 'BR')
    detail = [row for row in facts if row['codigo_cargo'] == 1 and row['uf'] != 'BR']
    if {row['uf'] for row in detail} != set(UFS + ['ZZ']):
        raise ValueError('Incomplete presidential territory coverage')
    fields = ('comparecimento', 'abstencoes', 'votos_total', 'votos_validos',
              'votos_nominais', 'votos_brancos', 'votos_nulos_total', 'secoes_totalizadas')
    for field in fields:
        if sum(row[field] for row in detail) != control[field]:
            raise ValueError(f'BR != UFs + abroad: {field}')


def write_csv(path, rows):
    if not rows:
        raise ValueError(f'Empty required result table: {path.name}')
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter=';')
        writer.writeheader()
        writer.writerows(rows)


def collect(workdir):
    cache = workdir / 'results-json'
    cache.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        documents = list(pool.map(lambda task: fetch(task, cache), tasks()))
    facts, candidates, parties, quotients = [], [], [], []
    for task, data, _ in documents:
        fact, cand, party, quotient = parse(task, data)
        facts.append(fact)
        # BR is only a reconciliation control; do not publish duplicate national rows.
        if task[0] != 'BR':
            candidates.extend(cand)
            parties.extend(party)
            if quotient is not None:
                quotients.append(quotient)
    reconcile_brazil(facts)
    for label, rows, keys in (
        ('facts', facts, ('chave_resultado',)),
        ('candidates', candidates, ('chave_resultado', 'id_candidato')),
        ('parties', parties, ('chave_resultado', 'numero_partido')),
    ):
        if len(rows) != len({tuple(row[key] for key in keys) for row in rows}):
            raise ValueError(f'Duplicate result keys: {label}')
    folder = workdir / 'raw' / 'resultados_primeiro_turno'
    folder.mkdir(parents=True, exist_ok=True)
    tables = {'abrangencia': [r for r in facts if r['uf'] != 'BR'],
              'candidatos': candidates, 'partidos': parties, 'quocientes': quotients}
    for name, rows in tables.items():
        write_csv(folder / f'{name}.csv', rows)
    manifest = dict(extracted_at_utc=datetime.now(timezone.utc).isoformat(), turno=1,
                    expected_documents=len(tasks()), downloaded_documents=len(documents),
                    reconciliation_passed=True, national_rows_published=False,
                    rows={name: len(rows) for name, rows in tables.items()},
                    sources=[source for _, _, source in documents])
    (workdir / 'results-sources.json').write_text(json.dumps(manifest, ensure_ascii=False,
                                                          indent=2), encoding='utf-8')
    print(json.dumps({key: value for key, value in manifest.items() if key != 'sources'}))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workdir', type=Path, default=Path('work'))
    collect(parser.parse_args().workdir)
