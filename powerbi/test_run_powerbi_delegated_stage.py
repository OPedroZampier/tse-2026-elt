from unittest.mock import patch
import pytest
from run_powerbi_delegated_stage import run_delegated_stage


@patch('run_powerbi_delegated_stage.stage')
@patch('run_powerbi_delegated_stage.run_with_private_reference')
@patch('run_powerbi_delegated_stage.GraphTransport')
@patch('run_powerbi_delegated_stage.exchange_refresh_token')
def test_stages_only_after_auth_and_build(exchange, transport, build, stage, tmp_path):
    output = tmp_path / 'output'
    exchange.return_value = 'access'
    build.return_value = {'batch_id': 'old', 'assembled': output / 'assembled'}
    stage.return_value = {'parts': 1, 'remote_content_verified': True}
    result = run_delegated_stage(tmp_path, output, '20261031T225800Z', 'refresh', 'github')
    transport.assert_called_once_with('access')
    stage.assert_called_once_with(output / 'assembled', output / 'reference' / 'manifest.json',
                                  transport.return_value, '20261031T225800Z')
    assert result['manifest_updated'] is False
    assert result['model_refresh_started'] is False


@patch('run_powerbi_delegated_stage.stage')
@patch('run_powerbi_delegated_stage.exchange_refresh_token', side_effect=RuntimeError('rotation failed'))
def test_failed_rotation_prevents_upload(exchange, stage, tmp_path):
    with pytest.raises(RuntimeError, match='rotation failed'):
        run_delegated_stage(tmp_path, tmp_path / 'output', '20261031T225800Z', 'refresh', 'github')
    stage.assert_not_called()
