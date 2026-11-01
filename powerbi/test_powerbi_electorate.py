import csv
import json
import pytest
from powerbi_electorate import BASE, DIMENSIONS, LOCATION, METRICS, MUNICIPAL, PROFILE, prepare


def test_aggregation_and_totals_across_chunks(tmp_path):
    columns = list(dict.fromkeys(LOCATION + PROFILE + METRICS))
    source = tmp_path / 'source.csv'
    with source.open('w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=columns, delimiter=';')
        writer.writeheader()
        for n in (1, 2):
            row = {column: 'x' for column in columns}
            row.update({metric: str(n) for metric in METRICS})
            writer.writerow(row)
    reference = tmp_path / 'reference.json'
    reference.write_text(json.dumps({'datasets': {
        'Eleitorado_Localidade': {'columns': LOCATION + METRICS},
        'eleitorado_cruzado': {'columns': PROFILE + METRICS},
        'eleitorado_municipio': {'columns': MUNICIPAL + METRICS}}}), encoding='utf-8')
    out = tmp_path / 'staging'
    result = prepare(source, reference, out, chunksize=1)
    assert result['source_totals']['QT_ELEITORES'] == 3
    assert result['rows']['eleitorado_municipio'] == len(DIMENSIONS)
    assert result['rows']['Eleitorado_Localidade'] == 1
    assert not result['publication_allowed'] and not (out / 'manifest.json').exists()
    with pytest.raises(FileExistsError):
        prepare(source, reference, out)
