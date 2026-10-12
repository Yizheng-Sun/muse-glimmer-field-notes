"""Exercise the API launcher with a fake evaluator; no API requests occur."""
import json
import os
from pathlib import Path
import pty
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from test_run_evaluation import FAKE_RUNNER, ROOT


class HaikuLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / 'checkout with spaces'
        (self.root / 'scripts').mkdir(parents=True)
        (self.root / 'config').mkdir()
        self.bin_dir = self.root / 'bin'
        self.bin_dir.mkdir()
        for script in ('run_evaluation.sh', 'run_haiku_evaluation.sh'):
            shutil.copy2(ROOT / 'scripts' / script, self.root / 'scripts')
        (self.root / 'scripts/evaluate_coding.py').write_text(FAKE_RUNNER)
        self.write_config(self.root / 'config/evaluation-haiku.json')
        (self.root / 'config/evaluation.json').write_text(json.dumps({'api_key_env': 'GLIMMER_API_KEY'}))
        self.command_file('hermes', 'exit 0\n')
        self.env = os.environ.copy()
        for name in ('ANTHROPIC_API_KEY', 'GLIMMER_API_KEY', 'glimmerapikey', 'RESUME_TEST_KEY',
                     'EVAL_DEFAULT_CONFIG', 'EVAL_EXPECT_PROVIDER', 'EVAL_LAUNCH_NAME'):
            self.env.pop(name, None)
        self.env['CASE_PYTHON'] = sys.executable
        self.env['EXPECTED_TEST_KEY'] = 'private-test-api-key'
        self.env['PATH'] = str(self.bin_dir) + os.pathsep + self.env['PATH']

    def write_config(self, path, key_env='ANTHROPIC_API_KEY'):
        path.write_text(json.dumps({'provider': 'anthropic', 'api_key_env': key_env,
                                    'hermes_command': ['hermes']}))

    def command_file(self, name, contents):
        path = self.bin_dir / name
        path.write_text('#!/bin/sh\n' + contents)
        path.chmod(0o755)
        return path

    def stop_background(self):
        for pid_file in (self.root / '.runs').glob('*-launch.pid'):
            try:
                pid = int(pid_file.read_text())
                if pid != os.getpid():
                    os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            pid_file.unlink()

    def tearDown(self):
        self.stop_background()
        self.temporary.cleanup()

    def command(self, *args):
        return ['bash', str(self.root / 'scripts/run_haiku_evaluation.sh'), *args]

    def launch(self, *args):
        return subprocess.run(self.command(*args), cwd=self.temporary.name, env=self.env,
                              stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=10)

    def test_inspection_is_api_free_and_does_not_require_hermes_or_create_runs(self):
        (self.bin_dir / 'hermes').unlink()
        for flag in ('--dry-run', '--help'):
            with self.subTest(flag=flag):
                result = self.launch(flag)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn('API key', result.stdout)
                self.assertFalse((self.root / '.runs').exists())

    def test_required_key_does_not_accept_glimmer_credentials_or_no_auth_placeholder(self):
        self.env['GLIMMER_API_KEY'] = self.env['EXPECTED_TEST_KEY']
        self.env['glimmerapikey'] = self.env['EXPECTED_TEST_KEY']
        result = self.launch()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Set ANTHROPIC_API_KEY', result.stderr)
        self.assertFalse((self.root / 'started.json').exists())
        self.assertFalse((self.root / '.runs/.haiku-evaluation-launch-lock').exists())

    def test_default_config_forwarding_separate_logs_and_duplicate_guard(self):
        self.env['ANTHROPIC_API_KEY'] = self.env['EXPECTED_TEST_KEY']
        runs = self.root / '.runs'
        runs.mkdir()
        glimmer_log = runs / 'evaluation-launch.log'
        glimmer_log.write_text('existing Glimmer results\n')
        # A separate Glimmer run must not prevent the API launcher starting.
        (runs / 'evaluation-launch.pid').write_text(str(os.getpid()))
        args = ['--cases', 'C02', '--efforts', 'low', '--budgets', 'small']
        result = self.launch(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        started = json.loads((self.root / 'started.json').read_text())
        self.assertEqual(started['argv'], ['--config', 'config/evaluation-haiku.json', *args])
        self.assertTrue(started['key_matches'])
        self.assertTrue(started['stdin_closed'])
        self.assertEqual(glimmer_log.read_text(), 'existing Glimmer results\n')
        latest = runs / 'haiku-evaluation-launch.log'
        self.assertTrue(latest.is_symlink())
        self.assertNotIn(self.env['EXPECTED_TEST_KEY'], result.stdout + result.stderr + latest.read_text())
        duplicate = self.launch()
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertIn('already running', duplicate.stderr)
        # Do not send SIGTERM to this unittest process during cleanup.
        (runs / 'evaluation-launch.pid').unlink()

    def test_config_override_and_resume_use_correct_required_credential_name(self):
        for resume in (False, True):
            with self.subTest(resume=resume):
                path = self.root / ('frozen batch' if resume else 'custom api config.json')
                if resume:
                    path.mkdir()
                    self.write_config(path / 'config.json', 'RESUME_TEST_KEY')
                    args = ['--resume=' + str(path)]
                else:
                    self.write_config(path, 'RESUME_TEST_KEY')
                    args = ['--config', str(path)]
                self.env['RESUME_TEST_KEY'] = self.env['EXPECTED_TEST_KEY']
                result = self.launch(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
                started = json.loads((self.root / 'started.json').read_text())
                self.assertEqual(started['argv'], ['--config', 'config/evaluation-haiku.json', *args])
                self.assertTrue(started['key_matches'])
                self.stop_background()

    def test_glimmer_resume_and_missing_hermes_fail_before_background_start(self):
        batch = self.root / 'glimmer batch'
        batch.mkdir()
        (batch / 'config.json').write_text(json.dumps({'api_key_env': 'GLIMMER_API_KEY'}))
        result = self.launch('--resume', str(batch))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('requires provider=anthropic', result.stderr)
        self.assertFalse((self.root / '.runs').exists())
        (self.bin_dir / 'hermes').unlink()
        self.env['PATH'] = str(self.bin_dir) + ':/usr/bin:/bin'
        missing = self.launch()
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn('Hermes is required', missing.stderr)
        self.assertFalse((self.root / '.runs').exists())

    def test_mac_keep_awake_watches_real_evaluator_pid(self):
        self.env['ANTHROPIC_API_KEY'] = self.env['EXPECTED_TEST_KEY']
        self.command_file('uname', 'printf "Darwin\\n"\n')
        self.command_file('caffeinate', 'printf "%s\\n" "$@" > caffeinate-args.txt\n')
        result = self.launch()
        self.assertEqual(result.returncode, 0, result.stderr)
        pid = (self.root / '.runs/haiku-evaluation-launch.pid').read_text().strip()
        self.assertEqual((self.root / 'caffeinate-args.txt').read_text().splitlines(), ['-i', '-w', pid])

    def test_bundled_python_fallback_for_mac_system_python_too_old(self):
        runtime = Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3'
        if not runtime.is_file():
            self.skipTest('The optional bundled Codex Python runtime is not installed.')
        self.env['CASE_PYTHON'] = str(self.root / 'deleted interpreter')
        for name in ('python3', 'python3.12', 'python3.13', 'python3.14'):
            self.command_file(name, 'exit 1\n')
        result = self.launch('--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / '.runs').exists())

    def test_interactive_key_is_hidden_and_empty_answer_is_rejected(self):
        for answer in (self.env['EXPECTED_TEST_KEY'], ''):
            with self.subTest(answer_is_empty=not answer):
                (self.root / 'started.json').unlink(missing_ok=True)
                master, slave = pty.openpty()
                process = subprocess.Popen(self.command(), cwd=self.temporary.name, env=self.env,
                                           stdin=slave, stdout=slave, stderr=slave)
                os.close(slave)
                output = b''
                answered = False
                deadline = time.monotonic() + 10
                try:
                    while time.monotonic() < deadline:
                        if select.select([master], [], [], 0.1)[0]:
                            try:
                                chunk = os.read(master, 65536)
                            except OSError:
                                break
                            if not chunk:
                                break
                            output += chunk
                            if b'API key (' in output and not answered:
                                os.write(master, (answer + '\n').encode())
                                answered = True
                        if process.poll() is not None and not select.select([master], [], [], 0)[0]:
                            break
                    status = process.wait(timeout=2)
                    self.assertTrue(answered, output.decode())
                    if answer:
                        self.assertEqual(status, 0, output.decode())
                        self.assertNotIn(answer.encode(), output)
                        self.assertTrue(json.loads((self.root / 'started.json').read_text())['key_matches'])
                    else:
                        self.assertNotEqual(status, 0, output.decode())
                        self.assertIn(b'An Anthropic API key is required', output)
                        self.assertFalse((self.root / 'started.json').exists())
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
                    os.close(master)
                    self.stop_background()


if __name__ == '__main__':
    unittest.main()
