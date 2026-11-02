import json
from unittest.mock import patch
import pytest
import weekly_activation as module


@patch('weekly_activation.activate')
@patch('weekly_activation.stage')
@patch('weekly_activation.run_with_private_reference')
@patch('weekly_activation.GraphTransport')
@patch('weekly_activation.exchange_refresh_token')
def test_only_activates_after_stage(exchange, transport, build, stage, activate, tmp_path):
    output = tmp_path / 'run'
    exchange.return_value = 'access'
    def prepare(*_):
        output.mkdir()
        return {'assembled': output / 'assembled'}
    build.side_effect = prepare
    stage.return_value = {'datasets': 19, 'parts': 55, 'remote_content_verified': True}
    activate.return_value = {'manifest_updated': True, 'model_refresh_started': False,
                             'remote_backup_verified': True}
    result = module.run(tmp_path, tmp_path / 'work', output, 'refresh', 'github')
    assert json.loads((output / 'receipt.json').read_text()) == stage.return_value
    activate.assert_called_once_with(output / 'assembled', output / 'reference' / 'manifest.json',
                                     output / 'receipt.json', output / 'manifest-backup.json',
                                     transport.return_value)
    assert result == {'manifest_updated': True, 'power_bi_refresh_requested': False,
                      'datasets': 19, 'parts': 55}


@patch('weekly_activation.activate')
@patch('weekly_activation.stage', side_effect=RuntimeError('verification failed'))
@patch('weekly_activation.run_with_private_reference')
@patch('weekly_activation.GraphTransport')
@patch('weekly_activation.exchange_refresh_token')
def test_failed_staging_never_activates(exchange, transport, build, stage, activate, tmp_path):
    output = tmp_path / 'run'
    def prepare(*_):
        output.mkdir()
        return {'assembled': output / 'assembled'}
    build.side_effect = prepare
    with pytest.raises(RuntimeError, match='verification failed'):
        module.run(tmp_path, tmp_path / 'work', output, 'refresh', 'github')
    activate.assert_not_called()


@patch('weekly_activation.exchange_refresh_token')
def test_missing_credentials_fail_before_network(exchange, tmp_path):
    with pytest.raises(ValueError, match='credentials'):
        module.run(tmp_path, tmp_path / 'work', tmp_path / 'run', '', 'github')
    exchange.assert_not_called()


@patch('weekly_activation.activate')
@patch('weekly_activation.stage')
@patch('weekly_activation.run_with_private_reference')
@patch('weekly_activation.GraphTransport')
@patch('weekly_activation.exchange_refresh_token')
def test_missing_backup_confirmation_reports_uncertain_result(exchange, transport, build, stage, activate, tmp_path):
    output = tmp_path / 'run'
    def prepare(*_):
        output.mkdir()
        return {'assembled': output / 'assembled'}
    build.side_effect = prepare
    stage.return_value = {'datasets': 19, 'parts': 55}
    activate.return_value = {'manifest_updated': True, 'model_refresh_started': False}
    with pytest.raises(RuntimeError, match='inspect the manifest'):
        module.run(tmp_path, tmp_path / 'work', output, 'refresh', 'github')
