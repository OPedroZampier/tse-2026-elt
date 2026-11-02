"""Build and verify a new private Power BI staging batch; never publish it."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

SCRIPTS = Path(__file__).resolve().parent


def run(repo: Path, reference: Path, output: Path, collected: Path | None = None, baseline_candidate: Path | None = None):
    repo, reference, output = repo.resolve(), reference.resolve(), output.resolve()
    if not (repo / 'pipeline' / 'ingest.py').is_file():
        raise ValueError('ELT repository does not contain pipeline/ingest.py')
    if not reference.is_file():
        raise ValueError('Reference manifest not found')
    if baseline_candidate is not None:
        baseline_candidate = baseline_candidate.resolve()
        if not baseline_candidate.is_file():
            raise ValueError('Candidate baseline not found')
    if output.exists():
        raise FileExistsError(output)
    if collected is not None:
        collected = collected.resolve()
        for name in ('sources.json', 'results-sources.json', 'runoff-sources.json'):
            if not (collected / name).is_file():
                raise ValueError(f'Collected source metadata missing: {name}')
    output.mkdir(parents=True, exist_ok=False)
    source = collected or output / 'source'

    def invoke(label, args, cwd):
        print(f'\n>>> {label}', flush=True)
        subprocess.run([sys.executable, *map(str, args)], cwd=cwd, check=True)

    if collected is None:
        for module in ('pipeline.ingest', 'pipeline.results', 'pipeline.runoff'):
            options = ['--refresh'] if module == 'pipeline.ingest' else []
            invoke(module, ['-m', module, '--workdir', source, *options], repo)
    raw = source / 'raw'
    direct, electorate, results, assembled = (output / x for x in ('direct', 'electorate', 'results', 'assembled'))
    invoke('Direct sources', [SCRIPTS / 'powerbi_direct_sources.py', '--raw', raw, '--reference', reference, '--output', direct], repo)
    invoke('Electorate', [SCRIPTS / 'powerbi_electorate.py', '--source', raw / 'eleitorado/perfil_eleitorado_2026_BRASIL.csv', '--reference', reference, '--output', electorate], repo)
    invoke('First and second rounds', [SCRIPTS / 'powerbi_results.py', '--work', source, '--reference', reference, '--output', results, '--candidate-source', raw / 'candidatos/consulta_cand_2026_BRASIL.csv'], repo)
    assemble_args = [SCRIPTS / 'powerbi_assemble_staging.py', '--reference', reference, '--direct', direct, '--electorate', electorate, '--results', results, '--output', assembled]
    if baseline_candidate is not None:
        assemble_args.extend(['--baseline-candidate', baseline_candidate])
    invoke('Assemble', assemble_args, repo)
    invoke('Independent verification', [SCRIPTS / 'verify_assembled_staging.py', '--root', assembled, '--reference', reference], repo)
    print('\nLocal verification completed. No OneDrive upload or online activation was performed.', flush=True)
    return assembled


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New, non-existing local directory')
    parser.add_argument('--collected', type=Path, help='Reuse collected inputs; does not fetch fresh data')
    parser.add_argument('--baseline-candidate', type=Path, help='First candidate part from the deployed manifest')
    args = parser.parse_args()
    run(args.repo, args.reference, args.output, args.collected, args.baseline_candidate)
