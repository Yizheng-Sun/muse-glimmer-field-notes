"""Exercise API-backed evaluation without credentials, network, or inference."""
from __future__ import annotations

import copy
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import evaluate_coding as runner


REPO_ROOT = Path(__file__).resolve().parents[1]
API_KEY = "test-anthropic-key-never-log"
FAKE_NATIVE_HERMES = '''import json, os, pathlib, sqlite3, sys, time
args = sys.argv[1:]
home = pathlib.Path(os.environ['HERMES_HOME'])
source = pathlib.Path.cwd()
session_id = 'fake_native_api_session'
if 'chat' in args:
    config = json.loads((home / 'config.yaml').read_text())
    effort = args[args.index('--reasoning') + 1]
    assert args[args.index('--provider') + 1] == 'anthropic'
    assert config['model']['provider'] == 'anthropic'
    assert config['model']['default'] == 'claude-haiku-5-5'
    assert config['agent']['reasoning_effort'] == effort
    assert 'chat_template_kwargs' not in json.dumps(config)
    assert 'glimmer-eval' not in json.dumps(config)
    assert os.environ['ANTHROPIC_API_KEY'] == 'test-anthropic-key-never-log'
    assert 'OPENAI_API_KEY' not in os.environ
    if not os.environ.get('FAKE_COMPATIBILITY_FAILURE'):
        (source / 'fixed.txt').write_text(effort)
    session = {'id':session_id, 'cwd':str(source), 'parent_session_id':None,
        'started_at':time.time()-0.05, 'ended_at':time.time(),
        'input_tokens':10, 'output_tokens':5, 'cache_read_tokens':100,
        'cache_write_tokens':20, 'reasoning_tokens':2,
        'api_call_count':1, 'tool_call_count':2,
        'messages':[{'role':'user','content':'repair'},
            {'role':'assistant','tool_calls':[{'id':'one'}, {'id':'two'}]},
            {'role':'tool'}, {'role':'tool'}, {'role':'assistant','content':'done'}]}
    (home / 'fake-export.json').write_text(json.dumps(session))
    with sqlite3.connect(home / 'state.db') as db:
        db.execute('CREATE TABLE sessions(id TEXT, cwd TEXT, parent_session_id TEXT)')
        db.execute('INSERT INTO sessions VALUES(?,?,NULL)', (session_id,str(source)))
    if os.environ.get('FAKE_COMPATIBILITY_FAILURE'):
        print('Haiku Hermes compatibility error: runtime changed')
        print('Session: '+session_id)
        sys.exit(2)
    print('Iteration budget reached')
    print('Session: '+session_id)
    sys.exit(1)
elif 'export' in args:
    target = pathlib.Path(args[args.index('export')+1])
    target.write_text((home / 'fake-export.json').read_text()+'\\n')
'''


class HaikuEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.batch = self.root / "batch"
        self.batch.mkdir()
        self.config = json.loads((REPO_ROOT / "config/evaluation-haiku.json").read_text())
        self.fake = self.root / "fake_native_hermes.py"
        self.fake.write_text(FAKE_NATIVE_HERMES)
        self.config.update(hermes_command=[sys.executable, str(self.fake)], upstream_checks=False)
        # These miniature offline inputs have their own manifest; production
        # fingerprints pin the full C01–C04 snapshots, not this fixture.
        self.config.pop("input_fingerprints", None)
        self.frozen = self.batch / "inputs/C02"
        (self.frozen / "base/src").mkdir(parents=True)
        (self.frozen / "base/src/example.py").write_text("broken = True\n")
        (self.frozen / "check.py").write_text(
            'import pathlib, sys\np = pathlib.Path(sys.argv[-1]); '
            'sys.exit(0 if (p / "fixed.txt").exists() else 1)\n'
        )
        (self.frozen / "case.json").write_text(json.dumps({"base_commit": "a" * 40}))
        (self.frozen / "prompt.md").write_text("Fix the example.\n")
        runner.save_json(self.frozen / "manifest.json", {
            "base": runner.files(self.frozen / "base"),
            "check_sha256": runner.digest(self.frozen / "check.py"),
            "prompt_sha256": runner.digest(self.frozen / "prompt.md"),
            "case_sha256": runner.digest(self.frozen / "case.json"),
        })

    def tearDown(self):
        self.temporary.cleanup()

    def write_config(self, config):
        path = self.root / "config.json"
        runner.save_json(path, config)
        return path

    def job(self, effort):
        return {
            "run_id": f"C02-small-{effort}-r01", "case_id": "C02",
            "budget_name": "small", "reasoning_effort": effort,
            "repeat": 1, "max_turns": 15, "max_seconds": 5,
        }

    def setup_attempt(self, config, batch, run, source):
        shutil.copytree(batch / "inputs/C02/base", source)

    def test_haiku_uses_the_identical_48_jobs_and_pinned_dependencies(self):
        glimmer = runner.load_config(REPO_ROOT / "config/evaluation.json")
        haiku = runner.load_config(REPO_ROOT / "config/evaluation-haiku.json")
        self.assertEqual(runner.make_jobs(haiku), runner.make_jobs(glimmer))
        self.assertEqual(len(runner.make_jobs(haiku)), 48)
        for name in ("pytest_version", "flit_core_version", "upstream_checks", "check_timeout_seconds"):
            self.assertEqual(haiku[name], glimmer[name], name)

    def test_haiku_pins_each_original_case_prompt_and_acceptance_checker(self):
        haiku = runner.load_config(REPO_ROOT / "config/evaluation-haiku.json")
        self.assertEqual(set(haiku["input_fingerprints"]), set(haiku["cases"]))
        for case in haiku["cases"]:
            with self.subTest(case=case):
                expected = haiku["input_fingerprints"][case]
                case_dir = REPO_ROOT / "cases/coding" / case
                for name, key in (("prompt.md", "prompt_sha256"), ("check.py", "check_sha256"), ("case.json", "case_sha256")):
                    self.assertEqual(expected[key], runner.digest(case_dir / name))
                self.assertEqual(expected["base_commit"], json.loads((case_dir / "case.json").read_text())["base_commit"])
                self.assertEqual(len(expected["base_tree_sha256"]), 64)

    def test_native_provider_sends_all_efforts_and_preserves_grading_and_metrics(self):
        with patch.object(runner, "setup_attempt", self.setup_attempt), patch.dict(
            os.environ, {"ANTHROPIC_API_KEY": API_KEY, "OPENAI_API_KEY": "unrelated-key"}
        ):
            for effort in ("low", "medium", "high", "xhigh"):
                with self.subTest(effort=effort):
                    job = self.job(effort)
                    self.assertFalse(runner.run_attempt(self.config, self.batch, job))
                    run = self.batch / "runs" / job["run_id"]
                    record = json.loads((run / "result.json").read_text())
                    self.assertEqual(record["verdict"], "PASS")
                    self.assertEqual(record["hermes_exit_code"], 1)
                    self.assertEqual(record["process_status"], "hermes_nonzero_exit")
                    self.assertEqual(record["metrics"]["total_tokens"], 135)
                    self.assertEqual(record["metrics"]["cache_read_tokens"], 100)
                    self.assertEqual(record["metrics"]["cache_write_tokens"], 20)
                    self.assertEqual(record["metrics"]["output_tokens"], 5)
                    self.assertEqual(record["metrics"]["reasoning_tokens"], 2)
                    self.assertEqual(record["metrics"]["api_calls"], 1)
                    self.assertEqual(record["metrics"]["tool_calls"], 2)
                    self.assertEqual(record["metrics"]["tool_iterations"], 1)
                    self.assertEqual(record["metrics"]["assistant_turns"], 2)
                    self.assertFalse(record["reasoning_verified"])
                    self.assertEqual((run / "source/fixed.txt").read_text(), effort)
                    for name in ("command.json", "result.json", "transcript.log", "hermes-home/config.yaml"):
                        self.assertNotIn(API_KEY, (run / name).read_text(), name)
        self.assertFalse((self.frozen / "base/fixed.txt").exists())

    def test_missing_api_key_fails_closed_but_local_server_keeps_placeholder(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex((ValueError, RuntimeError), "ANTHROPIC_API_KEY|API key"):
                runner.agent_env(self.config, self.root / "home", self.root / "source")
            glimmer = runner.load_config(REPO_ROOT / "config/evaluation.json")
            local_env = runner.agent_env(glimmer, self.root / "home", self.root / "source")
            self.assertEqual(local_env["GLIMMER_API_KEY"], "local-no-auth")
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": " "}):
            with self.assertRaisesRegex((ValueError, RuntimeError), "ANTHROPIC_API_KEY|API key"):
                runner.agent_env(self.config, self.root / "home", self.root / "source")

    def test_api_environment_cannot_inherit_another_account_or_endpoint(self):
        conflicting = {
            "ANTHROPIC_API_KEY": API_KEY, "ANTHROPIC_TOKEN": "oauth-token",
            "CLAUDE_CODE_OAUTH_TOKEN": "other-oauth", "ANTHROPIC_AUTH_TOKEN": "other-auth",
            "ANTHROPIC_BASE_URL": "https://attacker.test", "CLAUDE_CONFIG_DIR": "/old/account",
            "OPENAI_API_KEY": "other-api-key", "OPENAI_BASE_URL": "https://other.test",
            "HERMES_HOME": "/old/home", "TERMINAL_CWD": "/old/source", "PYTHONPATH": "/old/modules",
        }
        home, source = self.root / "home", self.root / "source"
        with patch.dict(os.environ, conflicting):
            env = runner.agent_env(self.config, home, source)
        for name in conflicting.keys() - {"ANTHROPIC_API_KEY", "HERMES_HOME", "TERMINAL_CWD"}:
            self.assertNotIn(name, env, name)
        self.assertEqual(env["ANTHROPIC_API_KEY"], API_KEY)
        self.assertEqual(env["HERMES_HOME"], str(home))
        self.assertEqual(env["TERMINAL_CWD"], str(source))

    def test_fatal_compatibility_error_stops_matrix_without_scoring_model_failure(self):
        job = self.job("low")
        with patch.object(runner, "setup_attempt", self.setup_attempt), patch.dict(
            os.environ, {"ANTHROPIC_API_KEY": API_KEY, "FAKE_COMPATIBILITY_FAILURE": "1"}
        ):
            self.assertTrue(runner.run_attempt(self.config, self.batch, job))
        run = self.batch / "runs" / job["run_id"]
        record = json.loads((run / "result.json").read_text())
        self.assertEqual(record["process_status"], "runtime_incompatible")
        self.assertEqual(record["verdict"], "SETUP_ERROR")
        self.assertEqual(record["hermes_exit_code"], 2)
        self.assertEqual(record["check_exit_code"], 1, "Retain the partial-source grade as evidence")
        self.assertEqual(record["metrics"]["total_tokens"], 135)
        self.assertFalse((run / "source/fixed.txt").exists())
        self.assertEqual(record["changed_files"], [])

    def test_cli_exits_two_after_runtime_error_and_does_not_start_remaining_jobs(self):
        config = copy.deepcopy(self.config)
        config.update(cases=["C02"], reasoning_efforts=["low", "high"], budgets=config["budgets"][:1])
        runner.save_json(self.batch / "config.json", config)
        jobs = runner.make_jobs(config)
        runner.save_json(self.batch / "jobs.json", jobs)
        runner.save_json(self.batch / "prepared.json", {})
        runner.save_json(self.batch / "wheel-hashes.json", {})
        (self.batch / "wheels").mkdir()
        with patch.object(runner, "preflight"), patch.object(
            runner, "setup_attempt", self.setup_attempt
        ), patch.dict(os.environ, {"ANTHROPIC_API_KEY": API_KEY, "FAKE_COMPATIBILITY_FAILURE": "1"}), patch.object(
            sys, "argv", ["runner", "--resume", str(self.batch)]
        ):
            self.assertEqual(runner.main(), 2)
        records = list((self.batch / "runs").glob("*/result.json"))
        self.assertEqual(len(records), 1)
        self.assertEqual(json.loads(records[0].read_text())["process_status"], "runtime_incompatible")
        self.assertFalse((self.batch / ".runner-lock").exists())

    def sdk_installer(self, argv, cwd, log, timeout=300, env=None):
        target = Path(argv[argv.index("--target") + 1])
        (target / "anthropic").mkdir(parents=True)
        (target / "anthropic/__init__.py").write_text("__version__ = '0.87.0'\n")
        metadata = target / "anthropic-0.87.0.dist-info/METADATA"
        metadata.parent.mkdir()
        metadata.write_text("Name: anthropic\nVersion: 0.87.0\n")
        (target / "docstring_parser").mkdir()
        (target / "docstring_parser/__init__.py").write_text("# Offline parser fixture\n")
        metadata = target / "docstring_parser-0.18.0.dist-info/METADATA"
        metadata.parent.mkdir()
        metadata.write_text("Name: docstring-parser\nVersion: 0.18.0\n")
        log.write_text("Fake offline SDK installation\n")
        return {"exit_code": 0, "status": "completed", "elapsed_seconds": 0.01}

    def test_batch_sdk_is_frozen_and_reused_without_another_install(self):
        with patch.object(runner, "require_logged", side_effect=self.sdk_installer) as installer:
            runner.ensure_haiku_sdk(self.config, self.batch)
        argv = installer.call_args.args[0]
        self.assertIn("anthropic==0.87.0", argv)
        self.assertIn("docstring-parser==0.18.0", argv)
        self.assertIn("--no-deps", argv)
        self.assertIn("--only-binary=:all:", argv)
        sdk = self.batch / "hermes-sdk"
        self.assertEqual(Path(argv[argv.index("--target") + 1]), sdk)
        manifest = self.batch / "hermes-sdk-hashes.json"
        frozen_manifest = manifest.read_bytes()
        self.assertEqual(json.loads(frozen_manifest), runner.files(sdk))
        with patch.object(runner, "require_logged") as installer:
            runner.ensure_haiku_sdk(self.config, self.batch)
        installer.assert_not_called()
        self.assertEqual(manifest.read_bytes(), frozen_manifest)
        self.assertEqual(self.config["_sdk_dir"], str(sdk.resolve()))
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": API_KEY, "HERMES_EVAL_SDK_DIR": "/unrelated/sdk"}):
            env = runner.agent_env(self.config, self.root / "home", self.root / "source")
        self.assertEqual(env["HERMES_EVAL_SDK_DIR"], str(sdk.resolve()))

    def test_changed_or_deleted_sdk_rejects_resume_instead_of_reinstalling(self):
        for change in ("modify", "delete"):
            with self.subTest(change=change):
                batch = self.root / change
                batch.mkdir()
                config = copy.deepcopy(self.config)
                with patch.object(runner, "require_logged", self.sdk_installer):
                    runner.ensure_haiku_sdk(config, batch)
                package = batch / "hermes-sdk/anthropic/__init__.py"
                if change == "modify":
                    package.write_text("__version__ = 'unexpected'\n")
                else:
                    shutil.rmtree(batch / "hermes-sdk")
                manifest = (batch / "hermes-sdk-hashes.json").read_bytes()
                with patch.object(runner, "require_logged") as installer:
                    with self.assertRaisesRegex(RuntimeError, "Frozen Anthropic SDK changed"):
                        runner.ensure_haiku_sdk(config, batch)
                installer.assert_not_called()
                self.assertEqual((batch / "hermes-sdk-hashes.json").read_bytes(), manifest)

    def test_sdk_install_without_expected_package_is_not_marked_ready(self):
        with patch.object(runner, "require_logged", return_value={"exit_code": 0, "status": "completed"}):
            with self.assertRaisesRegex(RuntimeError, "did not produce the expected package"):
                runner.ensure_haiku_sdk(self.config, self.batch)
        self.assertFalse((self.batch / "hermes-sdk-hashes.json").exists())
        self.assertNotIn("_sdk_dir", self.config)

    def test_sdk_without_required_parser_is_not_marked_ready(self):
        def incomplete_install(argv, cwd, log, timeout=300, env=None):
            result = self.sdk_installer(argv, cwd, log, timeout, env)
            shutil.rmtree(self.batch / "hermes-sdk/docstring_parser")
            return result
        with patch.object(runner, "require_logged", incomplete_install):
            with self.assertRaisesRegex(RuntimeError, "did not produce the expected package"):
                runner.ensure_haiku_sdk(self.config, self.batch)
        self.assertFalse((self.batch / "hermes-sdk-hashes.json").exists())
        self.assertNotIn("_sdk_dir", self.config)

    def test_api_configuration_rejects_endpoints_that_could_receive_credentials(self):
        for endpoint in (
            "http://api.anthropic.com", "https://api.anthropic.com.attacker.test",
            "https://attacker.test", "https://user:password@api.anthropic.com",
            "https://api.anthropic.com?proxy=attacker", "https://api.anthropic.com#token",
        ):
            with self.subTest(endpoint=endpoint):
                config = copy.deepcopy(self.config)
                config["base_url"] = endpoint
                with self.assertRaises(ValueError):
                    runner.load_config(self.write_config(config))
        config = copy.deepcopy(self.config)
        config["sampling"] = {"temperature": 1.0, "top_p": 0.95, "top_k": 64}
        with self.assertRaises(ValueError):
            runner.load_config(self.write_config(config))

    def test_api_configuration_cannot_silently_change_model_or_provider(self):
        for field, value in (
            ("model", "claude-haiku-other"),
            ("provider", "unknown"),
            ("api_key_env", "UNRELATED_SECRET"),
        ):
            with self.subTest(field=field):
                config = copy.deepcopy(self.config)
                config[field] = value
                with self.assertRaises(ValueError):
                    runner.load_config(self.write_config(config))

    def test_reused_inputs_are_verified_and_copied_without_source_downloads(self):
        config = copy.deepcopy(self.config)
        config["cases"] = ["C02"]
        target = self.root / "reused"
        target.mkdir()
        before = runner.files(self.batch / "inputs")
        with patch.object(runner, "require_logged", return_value={"exit_code": 0, "status": "completed"}) as logged:
            runner.prepare_batch(config, target, inputs_from=self.batch)
        self.assertEqual(runner.files(target / "inputs"), before)
        self.assertEqual(runner.files(self.batch / "inputs"), before)
        runner.verify_inputs(target, "C02")
        self.assertTrue(logged.called, "Dependency wheels should still be prepared")
        for call in logged.call_args_list:
            self.assertFalse(any("prepare_case.py" in str(item) for item in call.args[0]))
        provenance = json.loads((target / "input-provenance.json").read_text())
        self.assertEqual(provenance["source_batch"], str(self.batch.resolve()))
        self.assertEqual(provenance["cases"]["C02"]["prompt_sha256"], runner.digest(self.frozen / "prompt.md"))
        self.assertEqual(provenance["cases"]["C02"]["check_sha256"], runner.digest(self.frozen / "check.py"))
        self.assertEqual(provenance["cases"]["C02"]["case_sha256"], runner.digest(self.frozen / "case.json"))
        self.assertEqual(provenance["cases"]["C02"]["base_commit"], "a" * 40)
        self.assertEqual(len(provenance["cases"]["C02"]["base_tree_sha256"]), 64)

    def test_corrupted_reused_inputs_stop_before_download_or_agent(self):
        config = copy.deepcopy(self.config)
        config["cases"] = ["C02"]
        target = self.root / "reused"
        target.mkdir()
        (self.frozen / "base/src/example.py").write_text("corrupted = True\n")
        with patch.object(runner, "require_logged") as logged:
            with self.assertRaisesRegex(RuntimeError, "Frozen C02 baseline changed"):
                runner.prepare_batch(config, target, inputs_from=self.batch)
        logged.assert_not_called()

    def test_different_self_consistent_inputs_cannot_replace_the_original_snapshot(self):
        config = copy.deepcopy(self.config)
        config["cases"] = ["C02"]
        config["input_fingerprints"] = runner.verify_comparison_inputs(config, self.batch)
        (self.frozen / "prompt.md").write_text("A different, easier coding task.\n")
        manifest = json.loads((self.frozen / "manifest.json").read_text())
        manifest["prompt_sha256"] = runner.digest(self.frozen / "prompt.md")
        runner.save_json(self.frozen / "manifest.json", manifest)
        target = self.root / "reused"
        target.mkdir()
        with patch.object(runner, "require_logged") as logged:
            with self.assertRaisesRegex(RuntimeError, "inputs differ from the original Glimmer evaluation"):
                runner.prepare_batch(config, target, inputs_from=self.batch)
        logged.assert_not_called()

    def runtime_proof(self):
        return {
            "requests": {
                effort: {"thinking": {"type": "adaptive"}, "output_config": {"effort": effort}}
                for effort in ("low", "medium", "high", "xhigh")
            },
            "prior_thinking_replay_verified": True,
            "runtime_sha256": "b" * 64,
        }

    def preflight_logger(self, proof):
        def logged(argv, cwd, log, timeout=300, env=None):
            if "--check" in argv:
                runner.save_json(log, proof)
            elif "--help" in argv:
                log.write_text("--cli --oneshot --query-file --max-turns --run-budget --reasoning --ignore-rules --toolsets\n")
            else:
                log.write_text("Fake Hermes API test runtime\n")
            return {"exit_code": 0, "status": "completed", "elapsed_seconds": 0.01}
        return logged

    def test_native_preflight_uses_model_metadata_and_never_persists_the_key(self):
        proof = self.runtime_proof()
        opener = Mock()
        opener.open.return_value = io.StringIO(json.dumps({"id": "claude-haiku-5-5"}))
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": API_KEY}), patch.object(
            runner, "resolve_haiku_runtime", return_value=[sys.executable, str(self.fake)]
        ), patch.object(runner, "ensure_haiku_sdk"), patch.object(runner, "require_logged", self.preflight_logger(proof)), patch.object(
            runner, "build_opener", return_value=opener
        ):
            runner.preflight(self.config, self.batch)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertIsNone(request.data, "Preflight must not generate billable model output")
        self.assertEqual(request.full_url, "https://api.anthropic.com/v1/models/claude-haiku-5-5")
        self.assertEqual(request.get_header("X-api-key"), API_KEY)
        self.assertEqual(request.get_header("Anthropic-version"), "2023-06-01")
        self.assertEqual(json.loads((self.batch / "haiku-runtime.json").read_text()), proof)
        for name in ("haiku-runtime-check.json", "haiku-runtime.json", "hermes-help.log", "hermes-version.log", "server-models.json"):
            self.assertNotIn(API_KEY, (self.batch / name).read_text(), name)

    def test_resume_rejects_changed_runtime_before_another_model_lookup(self):
        original = self.runtime_proof()
        runner.save_json(self.batch / "haiku-runtime.json", original)
        changed = self.runtime_proof()
        changed["runtime_sha256"] = "c" * 64
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": API_KEY}), patch.object(
            runner, "resolve_haiku_runtime", return_value=[sys.executable, str(self.fake)]
        ), patch.object(runner, "ensure_haiku_sdk"), patch.object(runner, "require_logged", self.preflight_logger(changed)), patch.object(
            runner, "build_opener"
        ) as opener:
            with self.assertRaisesRegex(RuntimeError, "runtime or compatibility layer changed"):
                runner.preflight(self.config, self.batch)
        opener.assert_not_called()
        self.assertEqual(json.loads((self.batch / "haiku-runtime.json").read_text()), original)

    def test_preflight_missing_effort_or_model_fails_without_silent_fallback(self):
        incomplete = self.runtime_proof()
        incomplete["requests"].pop("xhigh")
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": API_KEY}), patch.object(
            runner, "resolve_haiku_runtime", return_value=[sys.executable, str(self.fake)]
        ), patch.object(runner, "ensure_haiku_sdk"), patch.object(runner, "require_logged", self.preflight_logger(incomplete)), patch.object(
            runner, "build_opener"
        ) as opener:
            with self.assertRaisesRegex(RuntimeError, "all four Haiku effort settings"):
                runner.preflight(self.config, self.batch)
        opener.assert_not_called()
        opener = Mock()
        opener.open.return_value = io.StringIO(json.dumps({"id": "claude-haiku-different"}))
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": API_KEY}), patch.object(
            runner, "resolve_haiku_runtime", return_value=[sys.executable, str(self.fake)]
        ), patch.object(runner, "ensure_haiku_sdk"), patch.object(runner, "require_logged", self.preflight_logger(self.runtime_proof())), patch.object(
            runner, "build_opener", return_value=opener
        ):
            with self.assertRaisesRegex(RuntimeError, "absent from the provider"):
                runner.preflight(self.config, self.batch)


if __name__ == "__main__":
    unittest.main()
