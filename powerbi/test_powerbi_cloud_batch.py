import csv
import io
from pathlib import Path
import tempfile
import unittest
from prepare_powerbi_cloud_batch import split_csv, replace_csv_document, encode_row


class CloudBatchTests(unittest.TestCase):
    def test_round_trip_multiline_and_identifiers(self):
        with tempfile.TemporaryDirectory(prefix='tse-cloud-test-') as temp:
            original = 'ID;NM;NR_CPF_CANDIDATO;VR\n1;"Nome; com quebra\nde linha";12345678901;"12,34"\n2;Outro;22222222222;0\n'
            limit = 3 + len(encode_row(['ID','NM','NR_CPF_CANDIDATO','VR'])) + len(encode_row(['1','Nome; com quebra\nde linha','','12,34']))
            contract = split_csv(io.StringIO(original), Path(temp)/'parts', max_bytes=limit)
            self.assertEqual(contract['rows'], 2)
            self.assertGreater(len(contract['files']), 1)
            rows = []
            for part in contract['files']:
                with (Path(temp)/'parts'/part['name']).open(encoding='utf-8-sig',newline='') as handle:
                    rows.extend(csv.DictReader(handle,delimiter=';'))
            self.assertEqual(rows[0], {'ID':'1','NM':'Nome; com quebra\nde linha','NR_CPF_CANDIDATO':'','VR':'12,34'})
            self.assertEqual(rows[1]['VR'],'0')

    def test_legacy_bytes_preserved(self):
        with tempfile.TemporaryDirectory(prefix='tse-cloud-test-') as temp:
            source = b'ID;NM\n1;Nome\x8d\x92\n'.decode('latin-1')
            contract = split_csv(io.StringIO(source),Path(temp)/'parts',output_encoding='latin-1')
            self.assertEqual(contract['encoding'],1252)
            raw = (Path(temp)/'parts'/contract['files'][0]['name']).read_bytes()
            self.assertIn(b'Nome\x8d\x92',raw)

    def test_csv_replacement_preserves_transformations(self):
        before = 'let Fonte=Csv.Document(File.Contents("D:/a(1).csv"),[Delimiter=";"]), T=Table.PromoteHeaders(Fonte) in T'
        after = replace_csv_document(before,'fnTSEFonte("A")')
        self.assertEqual(after,'let Fonte=fnTSEFonte("A"), T=Table.PromoteHeaders(Fonte) in T')

    def test_malformed_input_rejected(self):
        with tempfile.TemporaryDirectory(prefix='tse-cloud-test-') as temp:
            with self.assertRaises(ValueError):
                split_csv(io.StringIO('ID;VR\n1;2;3\n'),Path(temp)/'parts')


if __name__ == '__main__':
    unittest.main()
