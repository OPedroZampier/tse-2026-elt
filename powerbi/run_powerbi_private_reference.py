"""Build local Power BI staging from a verified private OneDrive reference.

Authentication is deliberately supplied by the caller as a Graph client. This
operation only reads the remote reference and writes to a new local directory;
it does not upload files, activate a manifest, or publish a dataset.
"""
from pathlib import Path

from fetch_powerbi_reference import fetch_reference
from run_powerbi_local_pipeline import run


def run_with_private_reference(repo: Path, output: Path, graph, collected: Path | None = None):
    output = output.resolve()
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True, exist_ok=False)
    reference = fetch_reference(graph, output / 'reference')
    assembled = run(repo, reference['manifest'], output / 'build', collected,
                    baseline_candidate=reference['baseline'])
    return {'batch_id': reference['batch_id'], 'assembled': assembled,
            'remote_write_performed': False}
