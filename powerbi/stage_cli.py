"""Run the private staging integration without activating its manifest."""
from datetime import datetime, timezone
import argparse
import os
from pathlib import Path

from run_powerbi_delegated_stage import run_delegated_stage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--collected', type=Path)
    args = parser.parse_args()
    refresh = os.environ.get('TSE_ONEDRIVE_REFRESH_TOKEN', '')
    github = os.environ.get('TSE_GITHUB_SECRETS_TOKEN', '')
    if not refresh or not github:
        raise SystemExit('Private staging credentials are not configured.')
    batch_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    result = run_delegated_stage(args.repo, args.output, batch_id, refresh, github, args.collected)
    receipt = result['receipt']
    if not receipt['remote_content_verified'] or result['manifest_updated'] or result['model_refresh_started']:
        raise RuntimeError('Unexpected private staging result')
    print(f"Private staging verified: {receipt['datasets']} datasets, {receipt['parts']} parts. "
          'No manifest or Power BI changes were made.')


if __name__ == '__main__':
    main()
