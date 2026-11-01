"""Generate five report tables from reconciled TSE result JSON, locally only."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse

OFFICES = {1, 3, 5, 6, 7, 8}
ELECTED = {'ELEITO', 'ELEITO POR MÉDIA', 'ELEITO POR QP'}
UFS = 'AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO'.split()


def integer(value):
    return int(value) if value not in ('', None) else 0


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def advances_to_runoff(first_status):
    value = first_status.upper()
    return int(value.startswith('2') and 'TURNO' in value)


def load_documents(work: Path):
    documents = []
    seen = set()
    for file in ('results-sources.json', 'runoff-sources.json'):
        audit = json.loads((work / file).read_text(encoding='utf-8-sig'))
        sources = audit['sources']
        if not audit['reconciliation_passed'] or len(sources) != audit['expected_documents']:
            raise ValueError(f'Incomplete source audit: {file}')
        for source in sources:
            name = Path(urlparse(source['url']).path).name
            path = work / 'results-json' / name
            content = path.read_bytes()
            if hashlib.sha256(content).hexdigest() != source['sha256']:
                raise ValueError(f'Source digest mismatch: {name}')
            data = json.loads(content)
            office = int(data['carg'][0]['cd'])
            key = (int(data['ele']), int(data['t']), data['cdabr'].upper(), office)
            match = re.fullmatch(r'([a-z]{2})-c(\d{4})-e(\d{6})-u\.json', name)
            if not match or (match[1].upper(), int(match[2]), int(match[3])) != (key[2], office, key[0]):
                raise ValueError(f'Source file and contents disagree: {name}')
            if key in seen or data['f'] != 'o' or office not in OFFICES:
                raise ValueError(f'Duplicate or invalid official result: {key}')
            if (key[1] == 1 and key[0] not in (6257, 6259)) or (key[1] == 2 and key[0] not in (6258, 6260)):
                raise ValueError(f'Invalid election/round: {key}')
            seen.add(key)
            documents.append(data)
    return documents


def validate_coverage(documents):
    """Check office/state coverage and the national presidential control."""
    indexed = {(int(d['ele']), int(d['t']), d['cdabr'].upper(), int(d['carg'][0]['cd'])): d for d in documents}
    first = {(6257, 1, uf, 1) for uf in ['BR', 'ZZ'] + UFS}
    first |= {(6259, 1, uf, office) for uf in UFS for office in (3, 5, 6, 8 if uf == 'DF' else 7)}
    if not first.issubset(indexed):
        raise ValueError('Incomplete first-round state and office coverage')
    runoff_states = []
    for uf in UFS:
        data = indexed[(6259, 1, uf, 3)]
        advancing = [c for group in data['carg'][0]['agr'] for party in group['par']
                     for c in party.get('cand', []) if advances_to_runoff(c['st'])]
        if advancing:
            if len(advancing) != 2:
                raise ValueError(f'Unexpected runoff count: {uf}')
            runoff_states.append(uf)
    second = {(6258, 2, uf, 1) for uf in ['BR', 'ZZ'] + UFS}
    second |= {(6260, 2, uf, 3) for uf in runoff_states}
    if set(indexed) != first | second:
        raise ValueError('Unexpected or missing result documents')
    for election, turn in ((6257, 1), (6258, 2)):
        br = indexed[(election, turn, 'BR', 1)]
        for field in ('tv', 'vv', 'vnom', 'vb', 'tvn'):
            detail = sum(integer(indexed[(election, turn, uf, 1)]['v'][field]) for uf in UFS + ['ZZ'])
            if detail != integer(br['v'][field]):
                raise ValueError(f'National reconciliation failed: round {turn}, {field}')
    for key in second:
        doc = indexed[key]
        if doc['tf'] != 's' or integer(doc['s']['st']) != integer(doc['s']['ts']):
            raise ValueError(f'Runoff not finalized: {key}')


def prepare(work: Path, reference: Path, output: Path, candidate_source: Path | None = None):
    if output.exists():
        raise FileExistsError(output)
    schemas = json.loads(reference.read_text(encoding='utf-8-sig'))['datasets']
    documents = load_documents(work)
    validate_coverage(documents)
    tables = {name: [] for name in ('PT_Controle', 'PT_Votos', 'PT_Partidos', 'PT_QE', 'PT_Cadastro')}
    status = {}
    first_round_status = {}
    for data in documents:
        uf = data['cdabr'].upper()
        if uf == 'BR':
            continue
        office, turn, election = int(data['carg'][0]['cd']), int(data['t']), int(data['ele'])
        common = dict(chave_resultado=f'{election}-{turn}-{uf}-{office}', eleicao=election,
                      turno=turn, abrangencia='EXTERIOR' if uf == 'ZZ' else 'UF', uf=uf,
                      codigo_cargo=office, cargo=data['carg'][0]['nmn'])
        sections, electorate, votes = data['s'], data['e'], data['v']
        fact = dict(common, data_geracao=data['dg'], hora_geracao=data['hg'],
                    data_totalizacao=data['dt'], hora_totalizacao=data['ht'], totalizacao_finalizada=data['tf'])
        for name, obj, key in [('secoes_total', sections, 'ts'), ('secoes_totalizadas', sections, 'st'),
                ('eleitorado', electorate, 'te'), ('eleitores_secoes_apuradas', electorate, 'esa'),
                ('comparecimento', electorate, 'c'), ('abstencoes', electorate, 'a'),
                ('votos_total', votes, 'tv'), ('votos_validos', votes, 'vv'), ('votos_nominais', votes, 'vnom'),
                ('votos_legenda', votes, 'vl'), ('votos_brancos', votes, 'vb'), ('votos_nulos_total', votes, 'tvn'),
                ('votos_nulos', votes, 'vn'), ('votos_nulos_tecnicos', votes, 'vnt'),
                ('votos_anulados', votes, 'van'), ('votos_anulados_sub_judice', votes, 'vansj')]:
            fact[name] = integer(obj.get(key))
        if fact['comparecimento'] + fact['abstencoes'] != fact['eleitores_secoes_apuradas']:
            raise ValueError(f'Attendance mismatch: {common["chave_resultado"]}')
        if fact['votos_validos'] != fact['votos_nominais'] + fact['votos_legenda']:
            raise ValueError(f'Valid votes mismatch: {common["chave_resultado"]}')
        tables['PT_Controle'].append(fact)
        if turn == 1 and office in (6, 7, 8):
            tables['PT_QE'].append(dict(uf=uf.lower(), codigo_cargo=office, cargo=common['cargo'],
                quociente_eleitoral=integer(data['carg'][0]['qe']), vagas=integer(data['carg'][0]['nv']),
                data_geracao=data['dg'], hora_geracao=data['hg']))
        for group in data['carg'][0]['agr']:
            for party in group['par']:
                tables['PT_Partidos'].append(dict(common, numero_partido=party['n'], partido=party['sg'],
                    nome_partido=party['nm'], votos_nominais=integer(party['tvtn']),
                    votos_legenda=integer(party.get('tvtl')) if office in (6, 7, 8) else 0,
                    votos_anulados=integer(party['tvan'])))
                for candidate in party.get('cand', []):
                    tables['PT_Votos'].append(dict(common, sq_candidato=candidate['sqcand'], numero_candidato=candidate['n'],
                        nome=candidate['nm'], nome_urna=candidate['nmu'], partido=party['sg'], resultado=candidate['st'],
                        destino_votos=candidate['dvt'], votos=integer(candidate['vap']),
                        percentual_oficial=float(candidate['pvapn'].replace(',', '.')) / 100))
                    key = (candidate['sqcand'], office)
                    if turn == 1:
                        candidate_status = candidate['st'].upper()
                        if key in first_round_status and first_round_status[key] != candidate_status:
                            raise ValueError(f'Conflicting first-round status for candidate {key}')
                        first_round_status[key] = candidate_status
                    if key not in status or turn >= status[key][0]:
                        status[key] = (turn, candidate['st'].upper())
    source = candidate_source or (work / 'raw' / 'candidatos' / 'consulta_cand_2026_BRASIL.csv')
    candidate_sha256 = file_sha256(source)
    with source.open(encoding='utf-8-sig', newline='') as file:
        for row in csv.DictReader(file, delimiter=';'):
            office = int(row['CD_CARGO'])
            if office not in OFFICES or row['NR_TURNO'] != '1':
                continue
            previous = row['DS_SIT_TOT_TURNO'].upper()
            final = status.get((row['SQ_CANDIDATO'], office), (1, previous))[1]
            first_status = first_round_status.get((row['SQ_CANDIDATO'], office), previous)
            tables['PT_Cadastro'].append(dict(sq_candidato=row['SQ_CANDIDATO'], turno=1, uf=row['SG_UF'],
                codigo_cargo=office, cargo=row['DS_CARGO'], nome_urna=row['NM_URNA_CANDIDATO'],
                partido=row['SG_PARTIDO'], genero=row['DS_GENERO'], raca_cor=row['DS_COR_RACA'],
                escolaridade=row['DS_GRAU_INSTRUCAO'], resultado=final, eleito=int(final in ELECTED),
                segundo_turno=advances_to_runoff(first_status),
                data_geracao=row['DT_GERACAO'], hora_geracao=row['HH_GERACAO']))
    if file_sha256(source) != candidate_sha256:
        raise ValueError('Candidate source changed during processing')
    for name, rows in tables.items():
        if not rows or any(list(row) != schemas[name]['columns'] for row in rows):
            raise ValueError(f'Empty or incompatible output: {name}')
    for name, keys in [('PT_Controle', ('chave_resultado',)), ('PT_Votos', ('chave_resultado','sq_candidato')),
                       ('PT_Cadastro', ('sq_candidato',)), ('PT_QE', ('uf','codigo_cargo'))]:
        keys_seen = [tuple(row[k] for k in keys) for row in tables[name]]
        if len(keys_seen) != len(set(keys_seen)):
            raise ValueError(f'Duplicate key: {name}')
    output.mkdir(parents=True, exist_ok=False)
    for name, rows in tables.items():
        with (output / f'{name}.csv').open('w', encoding='utf-8-sig', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=schemas[name]['columns'], delimiter=';')
            writer.writeheader()
            writer.writerows(rows)
    audit = {'status': 'incomplete', 'publication_allowed': False, 'candidate_source_sha256': candidate_sha256,
             'documents_verified': len(documents), 'rows': {name: len(rows) for name, rows in tables.items()}}
    (output / 'results-audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    return audit


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--candidate-source', type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.work, args.reference, args.output, args.candidate_source)))
