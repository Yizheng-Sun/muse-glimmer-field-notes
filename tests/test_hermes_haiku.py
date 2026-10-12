"""Verify scoped compatibility without an installed Hermes or API requests."""
from __future__ import annotations

from pathlib import Path
import json
import os
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import hermes_haiku as compat


def fake_runtime():
    def thinking(reasoning_config, model, effective_max_tokens):
        return {"legacy": model, "tokens": effective_max_tokens}

    policy = SimpleNamespace(model_preserves_prior_thinking=lambda model: model == "claude-opus-5-5")
    converter = SimpleNamespace(model_preserves_prior_thinking=policy.model_preserves_prior_thinking)
    adapter = SimpleNamespace(_thinking_kwargs=thinking)

    def build(model, messages, tools, max_tokens, reasoning_config, base_url=None, context_length=None, is_oauth=False):
        converted = []
        for message in messages:
            blocks = list(message.get("reasoning_details", [])) if converter.model_preserves_prior_thinking(model) else []
            blocks.append({"type": "text", "text": message["content"]})
            converted.append({"role": message["role"], "content": blocks})
        result = {"model": model, "messages": converted, "max_tokens": max_tokens or 128000,
                **adapter._thinking_kwargs(reasoning_config, model, max_tokens)}
        if tools:
            result["tools"] = tools
            result["tool_choice"] = {"type": "auto"}
        return result

    adapter.build_anthropic_kwargs = build
    return adapter, policy, converter


class HaikuCompatibilityTests(unittest.TestCase):
    def test_all_four_efforts_reach_native_builder_and_prior_thinking_is_kept(self):
        adapter, policy, converter = fake_runtime()
        required = compat.install_compatibility(adapter, policy, converter)
        self.assertEqual(required, {"effort_control": True, "prior_thinking": True})
        checked = compat.probe(adapter, policy)
        self.assertTrue(checked["prior_thinking_replay_verified"])
        self.assertTrue(checked["parallel_tool_use_disabled"])
        self.assertEqual(checked["default_max_output_tokens"], 128000)
        self.assertEqual(list(checked["requests"]), list(compat.EFFORTS))

    def test_other_models_and_disabled_thinking_keep_installed_behavior(self):
        adapter, policy, converter = fake_runtime()
        original = adapter._thinking_kwargs
        compat.install_compatibility(adapter, policy, converter)
        for model in ("claude-haiku-4-5", "claude-sonnet-5-5", "claude-haiku-5-5-custom"):
            config = {"enabled": True, "effort": "high"}
            self.assertEqual(adapter._thinking_kwargs(config, model, 90), original(config, model, 90))
        self.assertFalse(policy.model_preserves_prior_thinking("claude-haiku-4-5"))
        self.assertTrue(converter.model_preserves_prior_thinking("claude-opus-5-5"))
        config = {"enabled": False, "effort": "low"}
        self.assertEqual(adapter._thinking_kwargs(config, compat.MODEL, 90), original(config, compat.MODEL, 90))

    def test_unknown_runtime_shape_and_effort_fail_closed(self):
        adapter, policy, converter = fake_runtime()
        adapter._thinking_kwargs = lambda ignored: {}
        with self.assertRaisesRegex(RuntimeError, "unsupported Anthropic adapter"):
            compat.install_compatibility(adapter, policy, converter)
        adapter, policy, converter = fake_runtime()
        compat.install_compatibility(adapter, policy, converter)
        with self.assertRaises(ValueError):
            adapter._thinking_kwargs({"effort": "max"}, compat.MODEL, 90)

    def test_already_supported_runtime_is_accepted_and_stays_scoped(self):
        adapter, policy, converter = fake_runtime()
        adapter._thinking_kwargs = lambda config, model, cap: {
            "thinking": {"type": "adaptive", "display": "summarized"},
            "output_config": {"effort": config["effort"]}}
        policy.model_preserves_prior_thinking = lambda model: True
        converter.model_preserves_prior_thinking = policy.model_preserves_prior_thinking
        required = compat.install_compatibility(adapter, policy, converter)
        self.assertEqual(required, {"effort_control": False, "prior_thinking": False})
        self.assertTrue(compat.probe(adapter, policy)["prior_thinking_replay_verified"])

    def test_probe_rejects_dropped_effort_and_invalid_sampling(self):
        adapter, policy, converter = fake_runtime()
        with self.assertRaisesRegex(RuntimeError, "does not preserve low"):
            compat.probe(adapter, policy)
        compat.install_compatibility(adapter, policy, converter)
        original = adapter.build_anthropic_kwargs
        adapter.build_anthropic_kwargs = lambda **kwargs: {**original(**kwargs), "temperature": 1}
        with self.assertRaisesRegex(RuntimeError, "sampling parameters"):
            compat.probe(adapter, policy)

    def test_parallel_tool_hook_only_changes_exact_model_on_native_endpoint(self):
        adapter, policy, converter = fake_runtime()
        compat.install_compatibility(adapter, policy, converter)
        arguments = {"model": compat.MODEL, "messages": [], "tools": [{"type": "function"}],
                     "max_tokens": None, "reasoning_config": {"effort": "low"},
                     "base_url": "https://api.anthropic.com"}
        self.assertTrue(adapter.build_anthropic_kwargs(**arguments)["tool_choice"]["disable_parallel_tool_use"])
        for changes in ({"model": "claude-haiku-4-5"}, {"base_url": "https://other.example"},
                        {"base_url": "https://api.anthropic.com.other.example"}, {"tools": None}):
            with self.subTest(changes=changes):
                self.assertNotIn("disable_parallel_tool_use", adapter.build_anthropic_kwargs(**{**arguments, **changes}).get("tool_choice", {}))

    def test_batch_proof_rejects_wrapper_source_commit_and_interpreter_drift(self):
        fields = {"hermes_root": "/hermes", "hermes_python": "/python",
                  "hermes_commit": "a" * 40, "hermes_source_hashes": {"adapter.py": "abc"},
                  "compatibility_wrapper_sha256": "123"}
        with tempfile.TemporaryDirectory() as directory:
            proof = Path(directory) / "proof.json"
            proof.write_text(json.dumps({**fields, "requests": {}}))
            with patch.object(compat, "provenance", return_value=fields):
                compat.verify_runtime_proof(Path("/hermes"), proof)
            for field in fields:
                with self.subTest(field=field), patch.object(compat, "provenance", return_value={**fields, field: "changed"}):
                    with self.assertRaisesRegex(RuntimeError, "changed since batch preflight"):
                        compat.verify_runtime_proof(Path("/hermes"), proof)

    def test_fresh_home_borrows_only_installed_dependency_state_and_store(self):
        with tempfile.TemporaryDirectory() as directory:
            owner = Path(directory) / "owner"
            state = owner / "installs" / "key"
            state.mkdir(parents=True)
            (state / "facts.json").write_text("{}")
            root = Path(directory) / "hermes-agent"
            other = Path(directory) / "other"
            env = SimpleNamespace(install_state_dir=lambda project: other / "state",
                                  store_root=lambda project, **options: Path(os.environ["HERMES_HOME"]) / "tools",
                                  owning_home_root=lambda project: owner,
                                  dependency_home_root=lambda: owner, install_key=lambda project: "key")
            with patch.dict(os.environ, {"HERMES_HOME": "/fresh/profile"}), patch.object(compat, "_DEPENDENCY_CONTEXT", {}):
                compat.bind_installed_dependencies(root, env)
                self.assertEqual(os.environ["HERMES_HOME"], "/fresh/profile")
                self.assertEqual(env.install_state_dir(root), state)
                self.assertEqual(env.store_root(root), owner / "tools")
                self.assertEqual(env.install_state_dir(other), other / "state")
                self.assertEqual(env.store_root(other), Path("/fresh/profile/tools"))

    def test_local_sdk_tree_fingerprint_detects_edits_and_ignores_bytecode(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(compat, "_SDK_CONTEXT", {}), patch.object(sys, "path", list(sys.path)):
            target = Path(directory)
            (target / "anthropic").mkdir()
            source = target / "anthropic/__init__.py"
            source.write_text('__version__ = "0.87.0"\n')
            compat.configure_local_sdk(target)
            first = compat._SDK_CONTEXT["anthropic_sdk_tree_sha256"]
            (target / "anthropic/__pycache__").mkdir()
            (target / "anthropic/__pycache__/ignored.pyc").write_bytes(b"bytecode")
            compat.configure_local_sdk(target)
            self.assertEqual(first, compat._SDK_CONTEXT["anthropic_sdk_tree_sha256"])
            source.write_text('__version__ = "changed"\n')
            compat.configure_local_sdk(target)
            self.assertNotEqual(first, compat._SDK_CONTEXT["anthropic_sdk_tree_sha256"])

    def test_pending_recovery_and_missing_packages_stop_before_bootstrap(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "hermes"
            state = Path(directory) / "state"
            packages = Path(directory) / "site-packages"
            for folder in (root, state, packages, root / ".git"):
                folder.mkdir(parents=True)
            env = SimpleNamespace(install_state_dir=lambda project: state,
                                  committed_venv=lambda project: Path(directory) / "venv",
                                  site_packages=lambda environment: packages)
            compat.require_healthy_install(root, env)
            markers = (root / ".update-incomplete", root / ".lazy-refresh-incomplete",
                       root / ".hermes-update-zip-swap", root / ".git/hermes-update-pull",
                       state / ".repair-incomplete")
            for marker in markers:
                with self.subTest(marker=marker.name):
                    marker.write_text("pending")
                    with self.assertRaisesRegex(RuntimeError, "pending recovery"):
                        compat.require_healthy_install(root, env)
                    marker.unlink()
            packages.rmdir()
            with self.assertRaisesRegex(RuntimeError, "environment is unavailable"):
                compat.require_healthy_install(root, env)

    def test_sdk_import_requires_pinned_version(self):
        with patch.object(compat, "_SDK_CONTEXT", {}):
            for version in ("0.86.0", None):
                with self.subTest(version=version), patch.object(compat.importlib, "import_module", return_value=SimpleNamespace(__version__=version)):
                    with self.assertRaisesRegex(RuntimeError, "pinned to 0.87.0"):
                        compat.import_local_sdk()
            with patch.object(compat.importlib, "import_module", return_value=SimpleNamespace(__version__="0.87.0")):
                compat.import_local_sdk()
            self.assertEqual(compat._SDK_CONTEXT["anthropic_sdk_version"], "0.87.0")

    def test_provenance_rereads_dependency_facts_before_each_guard(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(compat, "_DEPENDENCY_CONTEXT", {}), patch.object(compat, "_SDK_CONTEXT", {}):
            root = Path(directory)
            for name in ("agent/anthropic_adapter.py", "agent/anthropic_thinking_policy.py",
                         "agent/anthropic_message_convert.py", "hermes_cli/main.py", "hermes_bootstrap.py", "pm/environments.py"):
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text("# runtime")
            facts = root / "facts.json"
            facts.write_text("original")
            compat._DEPENDENCY_CONTEXT.update(hermes_dependency_state=str(root), hermes_dependency_facts_sha256="cached")
            with patch.object(compat.subprocess, "check_output", return_value="commit"):
                first = compat.provenance(root)
                facts.write_text("changed")
                second = compat.provenance(root)
            self.assertNotEqual(first["hermes_dependency_facts_sha256"], "cached")
            self.assertNotEqual(first["hermes_dependency_facts_sha256"], second["hermes_dependency_facts_sha256"])


if __name__ == "__main__":
    unittest.main()
