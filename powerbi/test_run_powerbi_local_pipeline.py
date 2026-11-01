import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from run_powerbi_local_pipeline import run


class LocalPipelineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        (self.repo / 'pipeline').mkdir(parents=True)
        (self.repo / 'pipeline' / 'ingest.py').touch()
        self.reference = self.root / 'reference.json'
        self.reference.touch()
        self.output = self.root / 'new'

    @patch('run_powerbi_local_pipeline.subprocess.run')
    def test_runs_all_steps_without_publishing(self, invoke):
        run(self.repo, self.reference, self.output)
        self.assertEqual(invoke.call_count, 8)
        commands = [call.args[0] for call in invoke.call_args_list]
        self.assertIn('pipeline.ingest', commands[0])
        self.assertIn('--refresh', commands[0])
        self.assertTrue(all(call.kwargs['check'] for call in invoke.call_args_list))
        self.assertFalse(any('publish' in str(command).lower() for command in commands))

    @patch('run_powerbi_local_pipeline.subprocess.run', side_effect=RuntimeError('failure'))
    def test_failure_stops_immediately(self, invoke):
        with self.assertRaises(RuntimeError):
            run(self.repo, self.reference, self.output)
        self.assertEqual(invoke.call_count, 1)

    @patch('run_powerbi_local_pipeline.subprocess.run')
    def test_reuse_requires_source_manifests(self, invoke):
        collected = self.root / 'collected'
        collected.mkdir()
        with self.assertRaises(ValueError):
            run(self.repo, self.reference, self.output, collected)
        invoke.assert_not_called()
        self.assertFalse(self.output.exists())

    @patch('run_powerbi_local_pipeline.subprocess.run')
    def test_existing_output_is_never_overwritten(self, invoke):
        self.output.mkdir()
        with self.assertRaises(FileExistsError):
            run(self.repo, self.reference, self.output)
        invoke.assert_not_called()

    @patch('run_powerbi_local_pipeline.subprocess.run')
    def test_explicit_baseline_is_forwarded_to_assembly(self, invoke):
        baseline = self.root / 'candidate-baseline.csv'
        baseline.touch()
        run(self.repo, self.reference, self.output, baseline_candidate=baseline)
        commands = [call.args[0] for call in invoke.call_args_list]
        assembly = next(command for command in commands if any('powerbi_assemble_staging.py' in item for item in command))
        index = assembly.index('--baseline-candidate')
        self.assertEqual(assembly[index + 1], str(baseline.resolve()))

    @patch('run_powerbi_local_pipeline.subprocess.run')
    def test_missing_explicit_baseline_fails_before_creating_output(self, invoke):
        with self.assertRaisesRegex(ValueError, 'baseline not found'):
            run(self.repo, self.reference, self.output, baseline_candidate=self.root / 'missing.csv')
        self.assertFalse(self.output.exists())
        invoke.assert_not_called()


if __name__ == '__main__':
    unittest.main()
