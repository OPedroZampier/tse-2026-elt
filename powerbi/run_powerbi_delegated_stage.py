"""Rotate credentials, build and stage a private batch; do not activate it."""
from pathlib import Path

from github_refresh_secret import replace_refresh_secret
from powerbi_delegated_auth import exchange_refresh_token
from powerbi_onedrive_stage import GraphTransport, stage
from run_powerbi_private_reference import run_with_private_reference


def run_delegated_stage(repo: Path, output: Path, batch_id: str, refresh_token: str,
                        github_token: str, collected: Path | None = None):
    if output.exists():
        raise FileExistsError(output)
    access = exchange_refresh_token(
        refresh_token, lambda replacement: replace_refresh_secret(replacement, github_token))
    graph = GraphTransport(access)
    built = run_with_private_reference(repo, output, graph, collected)
    receipt = stage(built['assembled'], output / 'reference' / 'manifest.json', graph, batch_id)
    return {'baseline_batch_id': built['batch_id'], 'receipt': receipt,
            'manifest_updated': False, 'model_refresh_started': False}
