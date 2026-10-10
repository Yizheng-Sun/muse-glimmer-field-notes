"""Exercise orchestration without Hermes, downloads, or GPU inference."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import evaluate_coding as runner


FAKE_HERMES = '''import json, os, pathlib, sqlite3, sys, time
args = sys.argv[1:]
home = pathlib.Path(os.environ['HERMES_HOME'])
source = pathlib.Path.cwd()
session_id = 'fake_fresh_session'
if 'chat' in args:
    config = json.loads((home / 'config.yaml').read_text())
    effort = args[args.index('--reasoning') + 1]
    assert config['providers']['glimmer-eval']['extra_body']['chat_template_kwargs']['reasoning_strength'] == effort
    (source / 'fixed.txt').write_text(effort)
    session = {'id':session_id, 'cwd':str(source), 'parent_session_id':None,
        'started_at':time.time()-0.05,'ended_at':time.time(),
        'input_tokens':10,'output_tokens':5,'cache_read_tokens':100,'cache_write_tokens':0,
        'reasoning_tokens':2,'api_call_count':1,'tool_call_count':2,
        'messages':[{'role':'user','content':'repair'},
            {'role':'assistant','tool_calls':[{'id':'one'}, {'id':'two'}]},
            {'role':'tool'}, {'role':'tool'}, {'role':'assistant','content':'done'}]}
    (home / 'fake-export.json').write_text(json.dumps(session))
    with sqlite3.connect(home / 'state.db') as db:
        db.execute('CREATE TABLE sessions(id TEXT, cwd TEXT, parent_session_id TEXT)')
        db.execute('INSERT INTO sessions VALUES(?,?,NULL)', (session_id,str(source)))
    if os.environ.get('FAKE_SLEEP'):
        child = __import__('subprocess').Popen([sys.executable,'-c',
            'import pathlib,time; p=pathlib.Path("child-heartbeat"); [(p.write_text(str(time.time_ns())),time.sleep(.01)) for _ in range(3000)]'])
        (source / 'child.pid').write_text(str(child.pid))
        time.sleep(30)
    print('Iteration budget reached')
    print('Session: '+session_id)
    sys.exit(1)
elif 'export' in args:
    target=pathlib.Path(args[args.index('export')+1])
    target.write_text((home / 'fake-export.json').read_text()+'\\n')
'''


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.batch = self.root / 'batch'
        self.batch.mkdir()
        self.config = json.loads((runner.ROOT / 'config/evaluation.json').read_text())
        self.fake = self.root / 'fake_hermes.py'
        self.fake.write_text(FAKE_HERMES)
        self.config.update(hermes_command=[sys.executable, str(self.fake)], upstream_checks=False)
        frozen = self.batch / 'inputs/C02'
        (frozen / 'base/src').mkdir(parents=True)
        (frozen / 'base/src/example.py').write_text('broken = True\n')
        (frozen / 'check.py').write_text('import pathlib, sys\np=pathlib.Path(sys.argv[-1]); sys.exit(0 if (p / "fixed.txt").exists() else 1)\n')
        (frozen / 'case.json').write_text(json.dumps({'base_commit':'a'*40}))
        (frozen / 'prompt.md').write_text('Fix the example.\n')
        runner.save_json(frozen / 'manifest.json', {'base':runner.files(frozen / 'base'),
            'check_sha256':runner.digest(frozen / 'check.py'), 'prompt_sha256':runner.digest(frozen / 'prompt.md'),
            'case_sha256':runner.digest(frozen / 'case.json')})
        self.root_patch = patch.object(runner, 'ROOT', self.root)
        self.root_patch.start()

    def tearDown(self):
        self.root_patch.stop()
        self.temporary.cleanup()

    def job(self, effort='low'):
        return {'run_id':f'C02-small-{effort}-r01', 'case_id':'C02', 'budget_name':'small',
                'reasoning_effort':effort, 'repeat':1, 'max_turns':15, 'max_seconds':5}

    def setup_attempt(self, config, batch, run, source):
        shutil.copytree(batch / 'inputs/C02/base', source)

    def result(self, job):
        return json.loads((self.batch / 'runs' / job['run_id'] / 'result.json').read_text())

    def test_all_efforts_fresh_sources_and_budget_exit_can_pass_acceptance(self):
        with patch.object(runner, 'setup_attempt', self.setup_attempt):
            for effort in ('low','medium','high','xhigh'):
                job = self.job(effort)
                self.assertFalse(runner.run_attempt(self.config, self.batch, job))
                record = self.result(job)
                self.assertEqual(record['verdict'], 'PASS')
                self.assertEqual(record['hermes_exit_code'], 1)
                self.assertEqual(record['metrics']['tool_calls'], 2)
                self.assertEqual(record['metrics']['tool_iterations'], 1)
                self.assertEqual(record['metrics']['total_tokens'], 115)
                self.assertEqual(record['metrics']['assistant_turns'], 2)
                self.assertEqual((self.batch/'runs'/job['run_id']/'source/fixed.txt').read_text(), effort)
        self.assertFalse((self.batch / 'inputs/C02/base/fixed.txt').exists())

    def test_hard_timeout_retains_and_grades_partial_patch(self):
        job = self.job()
        job['max_seconds'] = 0.3
        with patch.object(runner, 'setup_attempt', self.setup_attempt), patch.dict(os.environ, {'FAKE_SLEEP':'1'}):
            self.assertFalse(runner.run_attempt(self.config, self.batch, job))
        record = self.result(job)
        self.assertEqual(record['process_status'], 'timed_out')
        self.assertEqual(record['verdict'], 'PASS')
        self.assertLess(record['elapsed_seconds'], 6)
        self.assertEqual(record['session_id'], 'fake_fresh_session')
        heartbeat = self.batch / 'runs' / job['run_id'] / 'source/child-heartbeat'
        before = heartbeat.read_text()
        time.sleep(0.05)
        self.assertEqual(heartbeat.read_text(), before, 'Child continued running after timeout')

    def test_checker_setup_error_is_not_model_failure(self):
        grader = self.batch / 'inputs/C02/check.py'
        grader.write_text('import sys; sys.exit(2)\n')
        manifest = json.loads((grader.parent / 'manifest.json').read_text())
        manifest['check_sha256'] = runner.digest(grader)
        runner.save_json(grader.parent / 'manifest.json', manifest)
        with patch.object(runner, 'setup_attempt', self.setup_attempt):
            runner.run_attempt(self.config, self.batch, self.job())
        self.assertEqual(self.result(self.job())['verdict'], 'SETUP_ERROR')

    def test_frozen_input_tamper_stops_before_agent(self):
        (self.batch / 'inputs/C02/base/src/example.py').write_text('changed')
        with patch.object(runner, 'setup_attempt') as setup:
            runner.run_attempt(self.config, self.batch, self.job())
        setup.assert_not_called()
        self.assertEqual(self.result(self.job())['process_status'], 'setup_error')

    def test_interruption_during_export_stops_matrix(self):
        actual_logged = runner.logged
        def interrupted_export(argv, *args, **kwargs):
            if 'export' in argv:
                return {'exit_code':-15, 'status':'interrupted', 'elapsed_seconds':0.01}
            return actual_logged(argv, *args, **kwargs)
        with patch.object(runner, 'setup_attempt', self.setup_attempt), patch.object(runner, 'logged', interrupted_export):
            self.assertTrue(runner.run_attempt(self.config, self.batch, self.job()))
        self.assertEqual(self.result(self.job())['process_status'], 'interrupted')

    def test_dead_lock_recovers_and_live_lock_blocks(self):
        lock = self.batch / '.runner-lock'
        lock.mkdir()
        runner.save_json(lock / 'owner.json', {'pid':2147483647, 'hostname':runner.socket.gethostname()})
        runner.acquire_lock(lock)
        with self.assertRaisesRegex(RuntimeError, 'live PID'):
            runner.acquire_lock(lock)

    def test_auxiliary_accounting_excludes_main_duplicate(self):
        home = self.root / 'home'
        home.mkdir()
        with sqlite3.connect(home / 'state.db') as db:
            db.execute('CREATE TABLE session_model_usage(session_id TEXT, task TEXT, input_tokens INT, output_tokens INT, cache_read_tokens INT, cache_write_tokens INT, reasoning_tokens INT, api_call_count INT)')
            db.execute('INSERT INTO session_model_usage VALUES(?,?,?,?,?,?,?,?)', ('s','',10,5,100,0,2,1))
            db.execute('INSERT INTO session_model_usage VALUES(?,?,?,?,?,?,?,?)', ('s','compression',3,2,7,0,1,1))
        usage = runner.auxiliary_metrics(home, 's')
        self.assertEqual(usage['auxiliary_total_tokens'], 12)
        self.assertEqual(usage['auxiliary_api_calls'], 1)

    def freeze_batch(self):
        self.config.update(cases=['C02'], reasoning_efforts=['low'], budgets=self.config['budgets'][:1])
        runner.save_json(self.batch / 'config.json', self.config)
        runner.save_json(self.batch / 'jobs.json', runner.make_jobs(self.config))
        runner.save_json(self.batch / 'prepared.json', {})
        runner.save_json(self.batch / 'wheel-hashes.json', {})
        (self.batch / 'wheels').mkdir()

    def test_resume_preserves_completed_result_without_new_agent(self):
        self.freeze_batch()
        job = runner.make_jobs(self.config)[0]
        result = self.batch / 'runs' / job['run_id'] / 'result.json'
        runner.save_json(result, {**job, 'verdict':'FAIL', 'process_status':'completed'})
        before = result.read_bytes()
        with patch.object(runner, 'preflight'), patch.object(runner, 'run_attempt') as attempt, patch.object(sys, 'argv', ['runner','--resume',str(self.batch)]):
            self.assertEqual(runner.main(), 0)
        attempt.assert_not_called()
        self.assertEqual(before, result.read_bytes())

    def test_resume_archives_incomplete_attempt_and_preserves_it_in_reports(self):
        self.freeze_batch()
        job = runner.make_jobs(self.config)[0]
        incomplete = self.batch / 'runs' / job['run_id']
        incomplete.mkdir(parents=True)
        (incomplete / 'transcript.log').write_text('unfinished attempt')
        with patch.object(runner, 'preflight'), patch.object(runner, 'setup_attempt', self.setup_attempt), patch.object(sys, 'argv', ['runner','--resume',str(self.batch)]):
            self.assertEqual(runner.main(), 0)
        archives = list((self.batch / 'incomplete').glob('*/transcript.log'))
        self.assertEqual(len(archives), 1)
        self.assertEqual(archives[0].read_text(), 'unfinished attempt')
        rows = [json.loads(line) for line in (self.batch / 'results.jsonl').read_text().splitlines()]
        self.assertEqual({r['verdict'] for r in rows}, {'UNKNOWN', 'PASS'})


if __name__ == '__main__':
    unittest.main()
