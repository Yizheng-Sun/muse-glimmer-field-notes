"""Test task semantics and real subprocess orchestration without model calls."""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import daily_cases
import daily_checks
import evaluate_daily as runner
from daily_test_support import reference_artifacts


FAKE_HERMES = r'''
import json, os, pathlib, re, sys, time
sys.path.insert(0, sys.argv[1])
sys.path.insert(0, sys.argv[2])
from daily_test_support import reference_artifacts
from urllib.request import urlopen
from urllib.error import HTTPError
args = sys.argv[3:]
home = pathlib.Path(os.environ['HERMES_HOME'])
workspace = pathlib.Path.cwd()
if 'chat' in args:
    assert not (home / 'session-stub.json').exists(), 'Session home was reused'
    config = json.loads((home/'config.yaml').read_text())
    assert config['memory']['memory_enabled'] is False
    assert config['fallback_providers'] == []
    case_id, variant = workspace.parent.name.split('-')[:2]
    case_path = workspace.parents[2] / 'inputs' / (case_id+'.json')
    case = json.loads(case_path.read_text())
    prompt_path = pathlib.Path(args[args.index('--query-file')+1])
    phase = prompt_path.parent.name
    base = 'http://fixture.invalid'
    if case['variants'][variant]['web_files']:
        text = '\n'.join(p.read_text() for p in workspace.rglob('*') if p.is_file())
        base = re.search(r'http://127\.0\.0\.1:\d+', text).group(0)
        for spec in case['variants'][variant]['checks']:
            if spec['kind'] == 'retrieval':
                for path in spec['required']:
                    try:
                        with urlopen(base+path) as response: response.read()
                    except HTTPError as exc:
                        assert exc.code == 404
    if case_id == 'D09' and phase == 'phase-01':
        expected = next(s['expected'] for s in case['variants'][variant]['checks'] if s.get('phase') == 1)
        (workspace/'outputs/day1.json').write_text(json.dumps(expected))
    else:
        if case_id == 'D05' and phase == 'phase-01':
            assert not (workspace/'inputs/editor.md').exists(), 'Editorial feedback was exposed early'
        if case_id == 'D05' and phase == 'phase-02':
            assert (workspace/'inputs/editor.md').exists(), 'Editorial feedback was not delivered'
        if case_id == 'D09':
            assert not (workspace/'inputs/day1-log.md').exists(), 'Raw log leaked into fresh second session'
            assert (workspace/'outputs/day1.json').exists()
        reference_artifacts(case, variant, workspace, base, inputs=False)
    mode = os.environ.get('FAKE_DAILY_MODE')
    if mode == 'bad-output':
        (workspace/'outputs/result.json').write_text('{}')
    if mode == 'tamper':
        case_path.write_text('{}')
    session = {'id': phase, 'cwd': str(workspace), 'parent_session_id': None,
        'started_at': time.time()-.01, 'ended_at': time.time(),
        'input_tokens': 10, 'output_tokens': 5, 'cache_read_tokens': 0, 'cache_write_tokens': 0,
        'reasoning_tokens': 0, 'api_call_count': 1, 'tool_call_count': 1,
        'messages': [{'role':'user'}, {'role':'assistant','tool_calls':[{'id':phase}]}, {'role':'tool'}, {'role':'assistant'}]}
    (home/'session-stub.json').write_text(json.dumps(session))
    print('Session: '+phase, flush=True)
    if mode == 'sleep': time.sleep(10)
    if mode == 'budget': sys.exit(1)
elif 'export' in args:
    path = pathlib.Path(args[args.index('export')+1])
    path.write_text((home/'session-stub.json').read_text()+'\n')
'''


class ArtifactChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.cases = daily_cases.build_cases()

    def tearDown(self):
        self.temp.cleanup()

    def reference(self, case_id, variant='normal'):
        case = self.cases[case_id]
        root = self.root / f'{case_id}-{variant}'
        snapshots = self.root / f'{case_id}-{variant}-snapshots'
        requests = reference_artifacts(case, variant, root, snapshots=snapshots)
        return case, root, snapshots, requests

    def check(self, case, root, snapshots, requests, variant='normal'):
        return daily_checks.check_case(case, variant, root, snapshots=snapshots, requests=requests)

    def test_all_45_fixtures_accept_reference_and_reject_missing_facts(self):
        for case_id in self.cases:
            for variant in daily_cases.VARIANTS:
                with self.subTest(case=case_id, variant=variant):
                    case, root, snapshots, requests = self.reference(case_id, variant)
                    result = self.check(case, root, snapshots, requests, variant)
                    self.assertTrue(result['passed'], result)
                    (root/'outputs/result.json').write_text('{}')
                    self.assertFalse(self.check(case, root, snapshots, requests, variant)['passed'])

    def test_json_order_and_equivalent_timezone_are_accepted(self):
        case, root, snapshots, requests = self.reference('D06')
        path = root/'outputs/result.json'
        value = json.loads(path.read_text())
        value['events'][0]['start'] = '2026-10-12T11:00:00Z'
        path.write_text(json.dumps(value))
        self.assertTrue(self.check(case, root, snapshots, requests)['passed'])

    def test_no_false_pass_from_claimed_completion(self):
        case, root, snapshots, requests = self.reference('D12')
        (root/'outputs/result.json').unlink()
        (root/'outputs/report.md').write_text('Everything has been completed correctly. '*8)
        self.assertFalse(self.check(case, root, snapshots, requests)['passed'])

    def test_nonfinite_duplicate_keys_and_boolean_numbers_are_rejected(self):
        case, root, snapshots, requests = self.reference('D01')
        path = root/'outputs/result.json'
        original = path.read_text()
        for malformed in ('{"x":NaN}', '{"x":1,"x":2}'):
            path.write_text(malformed)
            self.assertFalse(self.check(case, root, snapshots, requests)['passed'])
        value = json.loads(original)
        value['over_capacity'] = 0
        path.write_text(json.dumps(value))
        self.assertFalse(self.check(case, root, snapshots, requests)['passed'])

    def test_readonly_input_change_and_output_symlink_are_rejected(self):
        case, root, snapshots, requests = self.reference('D06')
        (root/'inputs/messages.json').write_text('[]')
        self.assertFalse(self.check(case, root, snapshots, requests)['passed'])
        target = root/'outputs/result.json'
        saved = self.root/'outside.json'
        target.rename(saved)
        target.symlink_to(saved)
        self.assertFalse(self.check(case, root, snapshots, requests)['passed'])

    def test_handovers_grade_first_phase_snapshot_not_later_repair(self):
        case, root, snapshots, requests = self.reference('D09')
        (snapshots/'phase-01/outputs/day1.json').write_text('{}')
        self.assertFalse(self.check(case, root, snapshots, requests)['passed'])

    def test_retrieval_is_required_even_with_correct_saved_facts(self):
        case, root, snapshots, requests = self.reference('D02')
        self.assertFalse(self.check(case, root, snapshots, [])['passed'])

    def test_meals_accept_alternative_plan_and_reject_impossible_leftovers(self):
        case, root, snapshots, requests = self.reference('D11')
        data = json.loads((root/'outputs/result.json').read_text())
        # A different feasible menu, with independently recomputed quantities.
        data['dinners'][0]['recipe_id'] = 'pasta'
        data['shopping'].update(rice=2, beans=0, pasta=4, tomato=6, eggs=4)
        data['cost_cents'] = 660
        (root/'outputs/result.json').write_text(json.dumps(data))
        self.assertTrue(self.check(case, root, snapshots, requests)['passed'])
        data['leftover_lunches'][0]['from_dinner_date'] = '2026-10-15'
        (root/'outputs/result.json').write_text(json.dumps(data))
        self.assertFalse(self.check(case, root, snapshots, requests)['passed'])

    def test_trip_accepts_waiting_but_rejects_teleporting(self):
        case, root, snapshots, requests = self.reference('D14')
        data = json.loads((root/'outputs/result.json').read_text())
        data['hotel_return'] = '14:00'
        (root/'outputs/result.json').write_text(json.dumps(data))
        self.assertTrue(self.check(case, root, snapshots, requests)['passed'])
        data['stops'][1]['arrival'] = '11:05'
        (root/'outputs/result.json').write_text(json.dumps(data))
        self.assertFalse(self.check(case, root, snapshots, requests)['passed'])

    def test_receipt_currency_and_refund_errors_fail(self):
        case, root, snapshots, requests = self.reference('D12', 'update')
        data = json.loads((root/'outputs/result.json').read_text())
        data['totals_cents']['GBP'] += 800
        (root/'outputs/result.json').write_text(json.dumps(data))
        self.assertFalse(self.check(case, root, snapshots, requests, 'update')['passed'])

    def test_folder_content_loss_fails(self):
        case, root, snapshots, requests = self.reference('D13')
        manifest = json.loads((root/'outputs/result.json').read_text())
        (root/manifest['moves'][0]['to']).write_text('corrupted')
        self.assertFalse(self.check(case, root, snapshots, requests)['passed'])


class RunnerChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.batch = self.root/'batch'
        self.batch.mkdir()
        self.fake = self.root/'fake.py'
        self.fake.write_text(FAKE_HERMES)
        self.config = json.loads((REPO/'config/evaluation-daily.json').read_text())
        self.config.update(cases=['D06'], variants=['normal'], repeats=1,
            budgets=[{'name':'test','max_turns':12,'max_seconds':5}],
            hermes_command=[sys.executable,str(self.fake),str(REPO/'scripts'),str(REPO/'tests')])

    def tearDown(self):
        self.temp.cleanup()

    def run_case(self, case_id='D06', variant='normal', mode=None):
        self.config.update(cases=[case_id], variants=[variant])
        runner.freeze_batch(self.config, self.batch)
        job = runner.make_jobs(self.config)[0]
        with patch.dict(os.environ, {'FAKE_DAILY_MODE': mode or ''}), contextlib.redirect_stdout(io.StringIO()):
            stopped = runner.run_attempt(self.config, self.batch, job)
        result = json.loads((self.batch/'runs'/job['run_id']/'result.json').read_text())
        return stopped, result, self.batch/'runs'/job['run_id']

    def test_subprocess_outputs_are_graded_and_usage_is_recorded(self):
        stopped, result, run = self.run_case()
        self.assertFalse(stopped)
        self.assertEqual(result['verdict'], 'PASS', result)
        self.assertEqual(result['metrics']['total_tokens'], 15)
        self.assertIsNone(result['auxiliary_total_tokens'])
        self.assertTrue((self.batch/'results.csv').exists())
        self.assertIn('Daily-task evaluation', (self.batch/'summary.md').read_text())

    def test_two_sessions_have_fresh_homes_and_only_saved_handover(self):
        _, result, run = self.run_case('D09', 'problem')
        self.assertEqual(result['verdict'], 'PASS', result)
        homes = [p['home'] for p in result['phases']]
        self.assertEqual(len(set(homes)), 2)
        self.assertEqual(sum(p['max_turns'] for p in result['phases']), 12)
        self.assertEqual(result['metrics']['total_tokens'], 30)
        self.assertFalse((run/'workspace/inputs/day1-log.md').exists())
        self.assertTrue((run/'snapshots/phase-01/outputs/day1.json').exists())

    def test_article_capture_uses_real_local_http_and_deduplicates(self):
        _, result, run = self.run_case('D02', 'problem')
        self.assertEqual(result['verdict'], 'PASS', result)
        requests = json.loads((run/'web-requests.json').read_text())
        self.assertIn({'path':'/articles/missing.html','status':404}, requests)

    def test_editorial_feedback_is_delivered_only_in_second_session(self):
        _, result, run = self.run_case('D05')
        self.assertEqual(result['verdict'], 'PASS', result)
        self.assertEqual(result['expected_phases'], 2)
        self.assertTrue((run/'snapshots/phase-01/outputs/draft.md').exists())

    def test_incorrect_artifact_is_failure(self):
        _, result, run = self.run_case(mode='bad-output')
        self.assertEqual(result['verdict'], 'FAIL')
        self.assertGreater(result['total_checks'], result['passed_checks'])

    def test_budget_exit_preserves_process_status_separately(self):
        _, result, run = self.run_case(mode='budget')
        self.assertEqual(result['verdict'], 'PASS', result)
        self.assertEqual(result['process_status'], 'hermes_nonzero_exit')

    def test_timeout_retains_and_checks_partial_artifacts(self):
        self.config['budgets'][0]['max_seconds'] = .3
        _, result, run = self.run_case(mode='sleep')
        self.assertEqual(result['process_status'], 'timed_out')
        self.assertEqual(result['verdict'], 'PASS', result)

    def test_frozen_grader_input_tamper_refuses_acceptance(self):
        _, result, run = self.run_case(mode='tamper')
        self.assertEqual(result['verdict'], 'EVIDENCE_ERROR', result)
        self.assertIn('Frozen case changed', result['error'])
        self.assertFalse((run/'check.json').exists())

    def test_resume_keeps_completed_result_without_new_model_call(self):
        _, result, run = self.run_case()
        before = (run/'result.json').read_bytes()
        with patch.object(runner.core, 'preflight'), patch.object(runner, 'run_attempt') as attempt, \
                patch.object(sys, 'argv', ['daily','--resume',str(self.batch)]), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(runner.main(), 0)
        attempt.assert_not_called()
        self.assertEqual(before, (run/'result.json').read_bytes())

    def test_resume_archives_incomplete_attempt(self):
        runner.freeze_batch(self.config, self.batch)
        job = runner.make_jobs(self.config)[0]
        run = self.batch/'runs'/job['run_id']
        run.mkdir(parents=True)
        (run/'transcript.log').write_text('unfinished evidence')
        with patch.object(runner.core, 'preflight'), patch.object(sys, 'argv', ['daily','--resume',str(self.batch)]), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(runner.main(), 0)
        archives = list((self.batch/'incomplete').glob('*/transcript.log'))
        self.assertEqual(len(archives), 1)
        self.assertEqual(archives[0].read_text(), 'unfinished evidence')
        rows = [json.loads(line) for line in (self.batch/'results.jsonl').read_text().splitlines()]
        self.assertEqual({r['verdict'] for r in rows}, {'UNKNOWN','PASS'})

    def test_missing_phase_metrics_remain_unknown(self):
        result = runner.aggregate_metrics([{'metrics':{'total_tokens':20}}, {'metrics_error':'export failed'}])
        self.assertIsNone(result['total_tokens'])
        self.assertTrue(result['metrics_warnings'])

    def test_config_rejects_duplicate_variants_and_too_few_phase_turns(self):
        self.config['variants'] = ['normal','normal']
        with self.assertRaises(ValueError): runner.validate_config(self.config)
        self.config.update(variants=['normal'], cases=['D09'])
        self.config['budgets'][0]['max_turns'] = 1
        with self.assertRaises(ValueError): runner.validate_config(self.config)

    def test_http_server_never_serves_filesystem_or_reviewer_paths(self):
        requests = []
        with runner.fixture_server({'/hello.html':'public fixture'}, requests) as base:
            self.assertEqual(urlopen(base+'/hello.html').read(), b'public fixture')
            with self.assertRaises(HTTPError) as error:
                urlopen(base+'/../inputs/D06.json')
            self.assertEqual(error.exception.code, 404)


class LauncherChecks(unittest.TestCase):
    def test_daily_and_coding_dry_runs_and_fixture_consistency(self):
        env = {**os.environ, 'CASE_PYTHON':sys.executable}
        for script, args, count in [('run_daily_evaluation.sh', [], '24 sequential daily-task runs'),
                                    ('run_daily_evaluation.sh', ['--all'], '90 sequential daily-task runs'),
                                    ('run_evaluation.sh', [], '48 sequential runs')]:
            result = subprocess.run(['bash',str(REPO/'scripts'/script),'--dry-run',*args], cwd=REPO, env=env,
                                    text=True, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(count, result.stdout)
        result = subprocess.run([sys.executable,str(REPO/'scripts/prepare_daily.py'),'--check'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
