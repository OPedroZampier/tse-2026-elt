"""Build a private, schema-compatible cloud batch without modifying the report.

Identifier values already absent from the model are blanked in raw inputs.
The remaining cells and existing M transformations are preserved. This creates
an initial migration snapshot, not a claim that the ELT-to-cloud sync is live.
"""
from __future__ import annotations
import argparse
import base64
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import zlib

# This legacy migration helper is not used by the staging workflow. A caller
# must explicitly supply the model directory when running it locally.
TABLES = None
TOKENS = ('CPF', 'CNPJ', 'EMAIL', 'TITULO_ELEITORAL', 'TELEFONE')


def sensitive(name):
    return any(token in name.upper() for token in TOKENS)


def replace_csv_document(query, replacement):
    start = query.index('Csv.Document(')
    depth, quoted, index = 0, False, start + len('Csv.Document')
    while index < len(query):
        char = query[index]
        if char == '"':
            if quoted and index + 1 < len(query) and query[index + 1] == '"':
                index += 2
                continue
            quoted = not quoted
        elif not quoted:
            depth += (char == '(') - (char == ')')
            if depth == 0:
                return query[:start] + replacement + query[index + 1:]
        index += 1
    raise ValueError('Unbalanced Csv.Document expression')


def encode_row(row, encoding='utf-8'):
    stream = io.StringIO(newline='')
    csv.writer(stream, delimiter=';', quoting=csv.QUOTE_ALL, lineterminator='\r\n').writerow(row)
    return stream.getvalue().encode(encoding)


def split_csv(source, destination, max_bytes=40_000_000, output_encoding='utf-8'):
    reader = csv.reader(source, delimiter=';')
    header = next(reader)
    redacted = [i for i, col in enumerate(header) if sensitive(col)]
    destination.mkdir(parents=True, exist_ok=False)
    header_bytes = (b'\xef\xbb\xbf' if output_encoding == 'utf-8' else b'') + encode_row(header, output_encoding)
    files, total, handle, size = [], 0, None, 0
    expected_projection = hashlib.sha256()
    try:
        for row in reader:
            if len(row) != len(header):
                raise ValueError('Unexpected source record width')
            for index in redacted:
                row[index] = ''
            data = encode_row(row, output_encoding)
            if len(data) + len(header_bytes) > max_bytes:
                raise ValueError('Single record exceeds part size')
            if handle is None or size + len(data) > max_bytes:
                if handle:
                    handle.close()
                name = f'part-{len(files) + 1:05d}.csv'
                handle = (destination / name).open('wb')
                handle.write(header_bytes)
                size = len(header_bytes)
                files.append(dict(name=name, rows=0))
            handle.write(data)
            size += len(data)
            files[-1]['rows'] += 1
            total += 1
            expected_projection.update(data)
    finally:
        if handle:
            handle.close()
    if not total:
        raise ValueError('Required migration source is empty')
    # Re-parse the actual output. No retained value may differ from its input.
    actual_projection = hashlib.sha256()
    for part in files:
        path = destination / part['name']
        with path.open(encoding='utf-8-sig' if output_encoding == 'utf-8' else output_encoding, newline='') as handle:
            parsed = csv.reader(handle, delimiter=';')
            if next(parsed) != header:
                raise ValueError('Part header mismatch')
            checked = 0
            for row in parsed:
                if len(row) != len(header) or any(row[i] for i in redacted):
                    raise ValueError('Identifier redaction or schema check failed')
                actual_projection.update(encode_row(row, output_encoding))
                checked += 1
            if checked != part['rows']:
                raise ValueError('Part row count mismatch')
        part.update(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    if actual_projection.digest() != expected_projection.digest():
        raise ValueError('Retained cell verification failed')
    return dict(rows=total, columns=header, encoding=65001 if output_encoding == 'utf-8' else 1252,
                redacted_columns=[header[i] for i in redacted],
                retained_values_verified=True, files=files)


def build(output):
    if TABLES is None:
        raise ValueError('No local model directory configured; migration is disabled')
    batch_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    batch_folder = output / 'batches' / batch_id
    query_folder = output / 'queries'
    query_folder.mkdir(parents=True, exist_ok=True)
    datasets = {}
    for path in sorted(TABLES.glob('*.tmdl')):
        text = path.read_text(encoding='utf-8')
        if not re.search(r'\bpartition .* = m\s*\n', text):
            continue
        query = text.split('\n\t\tsource =', 1)[1].split('\n\tannotation', 1)[0]
        query = '\n'.join(line[4:] if line.startswith('\t\t\t\t') else line for line in query.splitlines()).strip()
        filename = re.search(r'File\.Contents\(\s*"([^"]+)"', query)
        embedded = re.search(r'Binary\.FromText\("([^"]+)", BinaryEncoding.Base64\)', query)
        if not filename and not embedded:
            continue
        model_columns = re.findall(r'^\t\tsourceColumn: (.+)$', text, re.M)
        if any(sensitive(c) for c in model_columns):
            raise ValueError(f'Identifier retained in model: {path.stem}')
        for col in re.findall(r'\[([^\[\]]+)\]', query):
            if sensitive(col) and not col.startswith('"'):
                raise ValueError(f'Identifier used in calculation: {path.stem}')
        if filename:
            file = Path(filename[1])
            encoding_match = re.search(r'Encoding\s*=\s*(\d+)', query)
            # A Latin-1 byte-preserving round trip keeps every legacy byte intact,
            # including Windows-1252 undefined/control bytes. Power Query still
            # reads those output files as code page 1252, exactly as before.
            encoding = 'utf-8-sig' if encoding_match and encoding_match[1] == '65001' else 'latin-1'
            source = file.open(encoding=encoding, newline='')
        else:
            raw = zlib.decompress(base64.b64decode(embedded[1]), -15)
            source = io.StringIO(raw.decode('utf-8-sig'), newline='')
            encoding = 'utf-8-sig'
        with source:
            contract = split_csv(source, batch_folder / path.stem,
                                 output_encoding='utf-8' if encoding == 'utf-8-sig' else 'latin-1')
        datasets[path.stem] = contract
        adapted = replace_csv_document(query, f'fnTSEFonte("{path.stem}")')
        if 'File.Contents' in adapted or 'Binary.Decompress' in adapted:
            raise ValueError(f'Unconverted source: {path.stem}')
        (query_folder / f'{path.stem}.pq').write_text(adapted + '\n', encoding='utf-8-sig')
        print(json.dumps(dict(query=path.stem, rows=contract['rows'], parts=len(contract['files']), verified=True)), flush=True)
    if len(datasets) != 19:
        raise ValueError(f'Expected 19 external datasets, found {len(datasets)}')
    manifest = dict(batch_id=batch_id, status='ready', migration_snapshot=True,
                    destination='private OneDrive TSE-2026-Automacao-Privado', datasets=datasets,
                    note='Names, dates of birth and public TSE financial details remain. Not anonymized; not approved for additional public publication.')
    (output / f'manifest-{batch_id}.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(dict(batch_id=batch_id, datasets=len(datasets), files=sum(len(d['files']) for d in datasets.values()),
                          rows=sum(d['rows'] for d in datasets.values()), verified=True)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    build(parser.parse_args().output)
