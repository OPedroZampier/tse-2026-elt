import os
import sys
import unittest
from unittest.mock import patch

import stage_cli


class StageCliTests(unittest.TestCase):
    def test_missing_credentials_fails_before_upload(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(sys, 'argv', ['stage', '--repo', '.', '--output', 'new']), \
             patch.object(stage_cli, 'run_delegated_stage') as run:
            with self.assertRaises(SystemExit):
                stage_cli.main()
            run.assert_not_called()

    def test_upload_is_staging_only(self):
        result = {'receipt': {'remote_content_verified': True, 'datasets': 19, 'parts': 54},
                  'manifest_updated': False, 'model_refresh_started': False}
        with patch.dict(os.environ, {'TSE_ONEDRIVE_REFRESH_TOKEN': 'secret-one', 'TSE_GITHUB_SECRETS_TOKEN': 'secret-two'}, clear=True), \
             patch.object(sys, 'argv', ['stage', '--repo', '.', '--output', 'new']), \
             patch.object(stage_cli, 'run_delegated_stage', return_value=result) as run, \
             patch('builtins.print') as output:
            stage_cli.main()
            run.assert_called_once()
            self.assertNotIn('secret-', str(output.call_args))


if __name__ == '__main__':
    unittest.main()
