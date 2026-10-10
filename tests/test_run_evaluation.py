"""Exercise the Bash entry point without Hermes, downloads, or GPU inference."""
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


ROOT = Path(__file__).resolve().parents[1]
FAKE_RUNNER = '''import argparse, json, os, pathlib, sys, time
parser = argparse.ArgumentParser()
parser.add_argument('--config', type=pathlib.Path, default=pathlib.Path('config/evaluation.json'))
parser.add_argument('--resume', type=pathlib.Path)
parser.add_argument('--cases', nargs='+')
parser.add_argument('--efforts', nargs='+')
parser.add_argument('--budgets', nargs='+')
parser.add_argument('--dry-run', action='store_true')
args = parser.parse_args()
if args.dry_run:
    print('48 sequential runs; maximum agent time 9.33 hours.')
    print('C02-small-low-r01: 15 iterations / 300 seconds')
    sys.exit(0)
if os.environ.get('FAKE_STARTUP_FAILURE'):
    print('Evaluation stopped: fake server unavailable', flush=True)
    sys.exit(7)
path = args.resume / 'config.json' if args.resume else args.config
key_env = json.loads(path.read_text())['api_key_env']
pathlib.Path('started.json').write_text(json.dumps({
    'cwd': str(pathlib.Path.cwd()), 'argv': sys.argv[1:],
    'key_matches': os.environ.get(key_env) == os.environ['EXPECTED_TEST_KEY'],
    'stdin_closed': sys.stdin.read() == ''}))
print('Batch: fake-batch', flush=True)
time.sleep(30)
'''


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / 'checkout with spaces'
        (self.root / 'scripts').mkdir(parents=True)
        (self.root / 'config').mkdir()
        shutil.copy2(ROOT / 'scripts/run_evaluation.sh', self.root / 'scripts')
        (self.root / 'scripts/evaluate_coding.py').write_text(FAKE_RUNNER)
        (self.root / 'config/evaluation.json').write_text(json.dumps({'api_key_env': 'GLIMMER_API_KEY'}))
        self.env = os.environ.copy()
        for name in ('GLIMMER_API_KEY', 'glimmerapikey', 'RESUME_TEST_KEY'):
            self.env.pop(name, None)
        self.env['CASE_PYTHON'] = sys.executable
        self.env['EXPECTED_TEST_KEY'] = 'test-key-never-print-this'

    def stop_background(self):
        pid_file = self.root / '.runs/evaluation-launch.pid'
        if pid_file.exists():
            try:
                os.kill(int(pid_file.read_text()), signal.SIGTERM)
            except ProcessLookupError:
                pass
            pid_file.unlink()

    def tearDown(self):
        self.stop_background()
        self.temporary.cleanup()

    def command(self, *args):
        return ['bash', str(self.root / 'scripts/run_evaluation.sh'), *args]

    def launch(self, *args):
        # Invoking from outside the checkout also checks path handling.
        return subprocess.run(self.command(*args), cwd=self.temporary.name, env=self.env,
                              stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=10)

    def test_inspection_and_stale_python_fallback_need_no_credentials_or_run_files(self):
        bin_dir = self.root / 'bin'
        bin_dir.mkdir()
        (bin_dir / 'python3').symlink_to(sys.executable)
        self.env['CASE_PYTHON'] = str(self.root / '.runs/deleted-venv/bin/python')
        self.env['PATH'] = str(bin_dir) + os.pathsep + self.env['PATH']
        for flag in ('--dry-run', '--help'):
            with self.subTest(flag=flag):
                result = self.launch(flag)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn('API key', result.stdout)
                self.assertFalse((self.root / '.runs').exists())
        result = self.launch('--unknown-option')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / '.runs').exists())

    def test_resume_key_background_arguments_log_preservation_and_duplicate_guard(self):
        batch = self.root / 'frozen batch'
        batch.mkdir()
        (batch / 'config.json').write_text(json.dumps({'api_key_env': 'RESUME_TEST_KEY'}))
        self.env['RESUME_TEST_KEY'] = self.env['EXPECTED_TEST_KEY']
        runs = self.root / '.runs'
        runs.mkdir()
        (runs / 'evaluation-launch.log').write_text('previous launch evidence\n')
        args = ['--resume=' + str(batch)]
        result = self.launch(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        started = json.loads((self.root / 'started.json').read_text())
        self.assertEqual(started['argv'], args)
        self.assertEqual(Path(started['cwd']).resolve(), self.root.resolve())
        self.assertTrue(started['key_matches'])
        self.assertTrue(started['stdin_closed'])
        self.assertIn('background', result.stdout)
        self.assertNotIn(self.env['EXPECTED_TEST_KEY'], result.stdout + result.stderr)
        self.assertTrue((runs / 'evaluation-launch.log').is_symlink())
        archives = list(runs.glob('evaluation-launch-before-*.log'))
        self.assertEqual(len(archives), 1)
        self.assertEqual(archives[0].read_text(), 'previous launch evidence\n')
        latest = (runs / 'evaluation-launch.log').resolve()
        self.assertNotIn(self.env['EXPECTED_TEST_KEY'], latest.read_text())
        duplicate = self.launch(*args)
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertIn('already running', duplicate.stderr)
        self.assertEqual((runs / 'evaluation-launch.log').resolve(), latest)
        self.assertFalse((runs / '.evaluation-launch-lock').exists())

    def test_missing_noninteractive_key_and_fast_startup_failure_are_reported(self):
        missing = self.launch()
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn('Set GLIMMER_API_KEY', missing.stderr)
        self.assertFalse((self.root / 'started.json').exists())
        self.assertFalse((self.root / '.runs/.evaluation-launch-lock').exists())
        self.env['glimmerapikey'] = self.env['EXPECTED_TEST_KEY']
        self.env['FAKE_STARTUP_FAILURE'] = '1'
        failed = self.launch()
        self.assertEqual(failed.returncode, 7, failed.stdout + failed.stderr)
        self.assertIn('fake server unavailable', failed.stderr)
        self.assertNotIn('launched in the background', failed.stdout)

    def test_interactive_key_is_hidden_and_empty_answer_uses_no_auth_placeholder(self):
        for answer in ('test-key-never-print-this', ''):
            with self.subTest(answer_is_empty=not answer):
                self.env['EXPECTED_TEST_KEY'] = answer or 'local-no-auth'
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
                    self.assertEqual(process.wait(timeout=2), 0, output.decode())
                    self.assertTrue(answered)
                    if answer:
                        self.assertNotIn(answer.encode(), output)
                    self.assertTrue(json.loads((self.root / 'started.json').read_text())['key_matches'])
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
                    os.close(master)
                    self.stop_background()


if __name__ == '__main__':
    unittest.main()
