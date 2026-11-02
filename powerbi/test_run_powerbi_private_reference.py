from unittest.mock import patch

import pytest

from run_powerbi_private_reference import run_with_private_reference


@patch('run_powerbi_private_reference.run')
@patch('run_powerbi_private_reference.fetch_reference')
def test_passes_verified_reference_to_build(fetch, build, tmp_path):
    repo, output, collected = tmp_path / 'repo', tmp_path / 'output', tmp_path / 'collected'
    manifest, baseline = output / 'reference' / 'manifest.json', output / 'reference' / 'candidate-baseline.csv'
    fetch.return_value = {'batch_id': '20261031T225800Z', 'manifest': manifest, 'baseline': baseline}
    build.return_value = output / 'build' / 'assembled'
    graph = object()
    result = run_with_private_reference(repo, output, graph, collected)
    fetch.assert_called_once_with(graph, output / 'reference')
    build.assert_called_once_with(repo, manifest, output / 'build', collected, baseline_candidate=baseline)
    assert result['remote_write_performed'] is False


@patch('run_powerbi_private_reference.run')
@patch('run_powerbi_private_reference.fetch_reference', side_effect=ValueError('invalid reference'))
def test_invalid_reference_prevents_build(fetch, build, tmp_path):
    with pytest.raises(ValueError, match='invalid reference'):
        run_with_private_reference(tmp_path / 'repo', tmp_path / 'output', object())
    build.assert_not_called()


def test_existing_output_is_preserved(tmp_path):
    with pytest.raises(FileExistsError):
        run_with_private_reference(tmp_path, tmp_path, object())
