"""Build, verify, and activate a fresh batch after a successful TSE pipeline."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from activate_onedrive_batch import activate
from github_refresh_secret import replace_refresh_secret
from powerbi_delegated_auth import exchange_refresh_token
from powerbi_onedrive_stage import GraphTransport, stage
from run_powerbi_private_reference import run_with_private_reference


def run(repo: Path, collected: Path, output: Path, refresh: str, github: str):
    if not refresh or not github:
        raise ValueError('Private integration credentials are required')
    if output.exists():
        raise FileExistsError(output)
    access = exchange_refresh_token(refresh, lambda replacement: replace_refresh_secret(replacement, github))
    graph = GraphTransport(access)
    built = run_with_private_reference(repo, output, graph, collected)
    reference = output / 'reference' / 'manifest.json'
    batch = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    receipt = stage(built['assembled'], reference, graph, batch)
    receipt_path = output / 'receipt.json'
    with receipt_path.open('x', encoding='utf-8') as f:
        json.dump(receipt, f, ensure_ascii=False)
    result = activate(built['assembled'], reference, receipt_path, output / 'manifest-backup.json', graph)
    if (not result.get('manifest_updated') or not result.get('remote_backup_verified')
            or result.get('model_refresh_started') is not False):
        raise RuntimeError('Unexpected activation result; inspect the manifest before retrying')
    return {'manifest_updated': True, 'power_bi_refresh_requested': False,
            'datasets': receipt['datasets'], 'parts': receipt['parts']}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--collected', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    outcome = run(args.repo, args.collected, args.output,
                  os.environ.get('TSE_ONEDRIVE_REFRESH_TOKEN', ''),
                  os.environ.get('TSE_GITHUB_SECRETS_TOKEN', ''))
    print(json.dumps(outcome), flush=True)
