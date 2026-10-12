#!/usr/bin/env python3
"""Run installed Hermes with a process-local Haiku 5.5 compatibility fix.

Older Hermes releases classify every Haiku model as non-thinking and discard
its prior thinking blocks. Only claude-haiku-5-5 is changed here; installed
files, prompts, tools, approvals, and other model behavior stay untouched.
"""
from __future__ import annotations

import argparse
from functools import wraps
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlparse

MODEL = "claude-haiku-5-5"
EFFORTS = ("low", "medium", "high", "xhigh")
SDK_VERSION = "0.87.0"
_DEPENDENCY_CONTEXT = {}
_SDK_CONTEXT = {}


def bind_installed_dependencies(root, environments=None):
    """Borrow installed packages while config, DB, and scratch use the fresh home."""
    if environments is None:
        from pm import environments
    try:
        original_state = environments.install_state_dir
        original_store = environments.store_root
        owner = environments.owning_home_root(root) or environments.dependency_home_root()
        state = owner / "installs" / environments.install_key(root)
    except AttributeError as error:
        raise RuntimeError("Installed Hermes dependency layout is unsupported") from error
    if not (state / "facts.json").is_file():
        raise RuntimeError("Installed Hermes has no committed dependency state")
    previous_home = os.environ.get("HERMES_HOME")
    try:
        os.environ["HERMES_HOME"] = str(owner)
        store = original_store(root, honor_runtime_override=False)
    finally:
        if previous_home is None:
            os.environ.pop("HERMES_HOME", None)
        else:
            os.environ["HERMES_HOME"] = previous_home
    resolved = root.resolve()

    def installed_state(project_root):
        return state if Path(project_root).resolve() == resolved else original_state(project_root)

    def installed_store(project_root, *, honor_runtime_override=True):
        return store if Path(project_root).resolve() == resolved else original_store(project_root, honor_runtime_override=honor_runtime_override)

    environments.install_state_dir = installed_state
    environments.store_root = installed_store
    # owning_home_root imports the launcher to identify the install owner; it
    # captures store_root by value before the hook above is installed.
    launcher = sys.modules.get("hermes_cli._launchers")
    if launcher is not None and getattr(launcher, "store_root", None) is original_store:
        launcher.store_root = installed_store
    _DEPENDENCY_CONTEXT.update(hermes_dependency_state=str(state), hermes_dependency_store=str(store),
                               hermes_dependency_facts_sha256=hashlib.sha256((state / "facts.json").read_bytes()).hexdigest())


def require_healthy_install(root, environments=None):
    """Refuse pending recovery instead of letting bootstrap repair the install."""
    if environments is None:
        from pm import environments
    dot_git = root / ".git"
    git_dir = dot_git
    if dot_git.is_file():
        content = dot_git.read_text(encoding="utf-8-sig").strip()
        if content.startswith("gitdir:"):
            git_dir = root / content[len("gitdir:"):].strip()
    markers = (root / ".update-incomplete", root / ".lazy-refresh-incomplete",
               root / ".hermes-update-zip-swap", git_dir / "hermes-update-pull",
               environments.install_state_dir(root) / ".repair-incomplete")
    if any(marker.exists() for marker in markers):
        raise RuntimeError("Installed Hermes has pending recovery; repair it separately before evaluation")
    try:
        environment = environments.committed_venv(root)
        healthy = environment is not None and environments.site_packages(environment).is_dir()
    except (AttributeError, RuntimeError) as error:
        raise RuntimeError("Installed Hermes committed dependency environment is unavailable") from error
    if not healthy:
        raise RuntimeError("Installed Hermes committed dependency environment is unavailable; repair it separately before evaluation")


def configure_local_sdk(path):
    """Expose a batch-local pure-Python SDK without mutating Hermes packages."""
    directory = Path(path).resolve()
    if not (directory / "anthropic/__init__.py").is_file():
        raise RuntimeError("Batch-local Anthropic SDK is missing")
    hashes = {str(file.relative_to(directory)): hashlib.sha256(file.read_bytes()).hexdigest()
              for file in sorted(directory.rglob("*"))
              if file.is_file() and "__pycache__" not in file.parts and file.suffix != ".pyc"}
    _SDK_CONTEXT.update(anthropic_sdk_directory=str(directory),
                        anthropic_sdk_tree_sha256=hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()).hexdigest())
    sys.path.insert(0, str(directory))


def import_local_sdk():
    sdk = importlib.import_module("anthropic")
    if getattr(sdk, "__version__", None) != SDK_VERSION:
        raise RuntimeError(f"Batch-local Anthropic SDK must be pinned to {SDK_VERSION}")
    _SDK_CONTEXT["anthropic_sdk_version"] = sdk.__version__


def install_compatibility(adapter, policy, converter):
    """Patch known adapter hooks, refusing incompatible Hermes structures."""
    try:
        thinking = adapter._thinking_kwargs
        build = adapter.build_anthropic_kwargs
        preserves = policy.model_preserves_prior_thinking
        converted_preserves = converter.model_preserves_prior_thinking
        inspect.signature(thinking).bind({"effort": "low"}, MODEL, 16384)
        inspect.signature(preserves).bind(MODEL)
        inspect.signature(converted_preserves).bind(MODEL)
        inspect.signature(adapter.build_anthropic_kwargs).bind(
            model=MODEL, messages=[], tools=None, max_tokens=16384,
            reasoning_config={"effort": "low"}, base_url="https://api.anthropic.com",
            context_length=131072, is_oauth=False,
        )
    except (AttributeError, TypeError, ValueError) as error:
        raise RuntimeError("Installed Hermes has an unsupported Anthropic adapter; compatibility check stopped") from error

    previous = thinking({"enabled": True, "effort": "low"}, MODEL, 16384)
    if not isinstance(previous, dict) or not isinstance(previous.get("output_config", {}), dict):
        raise RuntimeError("Installed Hermes has an unsupported Anthropic thinking result")
    required = {
        "effort_control": previous.get("output_config", {}).get("effort") != "low",
        "prior_thinking": not preserves(MODEL) or not converted_preserves(MODEL),
    }

    def haiku_thinking(reasoning_config, model, effective_max_tokens):
        if model != MODEL:
            return thinking(reasoning_config, model, effective_max_tokens)
        if reasoning_config.get("enabled") is False:
            return thinking(reasoning_config, model, effective_max_tokens)
        effort = reasoning_config.get("effort", "medium")
        if effort not in EFFORTS:
            raise ValueError(f"Haiku evaluation effort must be one of {EFFORTS}; received {effort!r}")
        return {"thinking": {"type": "adaptive", "display": "summarized"},
                "output_config": {"effort": effort}}

    def haiku_preserves(model):
        return True if model == MODEL else preserves(model)

    def converted_haiku_preserves(model):
        return True if model == MODEL else converted_preserves(model)

    adapter._thinking_kwargs = haiku_thinking
    policy.model_preserves_prior_thinking = haiku_preserves
    # The converter imports the function by value, so update its cached hook too.
    converter.model_preserves_prior_thinking = converted_haiku_preserves

    @wraps(build)
    def haiku_build(*args, **kwargs):
        arguments = inspect.signature(build).bind(*args, **kwargs).arguments
        result = build(*args, **kwargs)
        endpoint = urlparse(arguments.get("base_url") or "")
        if arguments.get("model") == MODEL and endpoint.scheme == "https" and endpoint.hostname == "api.anthropic.com" and result.get("tools"):
            choice = result.get("tool_choice") or {"type": "auto"}
            if not isinstance(choice, dict):
                raise RuntimeError("Installed Hermes has an unsupported Anthropic tool choice")
            result["tool_choice"] = {**choice, "disable_parallel_tool_use": True}
        return result

    adapter.build_anthropic_kwargs = haiku_build
    return required


def probe(adapter, policy):
    """Build native requests locally; no client, credentials, or API calls."""
    requests = {}
    tools = [{"type": "function", "function": {
        "name": "read_example", "description": "Local compatibility probe.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}}]
    for effort in EFFORTS:
        kwargs = adapter.build_anthropic_kwargs(
            model=MODEL, messages=[{"role": "user", "content": "Compatibility probe."}],
            tools=tools, max_tokens=None, reasoning_config={"enabled": True, "effort": effort},
            is_oauth=False, context_length=131072, base_url="https://api.anthropic.com",
        )
        if kwargs.get("model") != MODEL or kwargs.get("thinking", {}).get("type") != "adaptive" or kwargs.get("output_config", {}).get("effort") != effort:
            raise RuntimeError(f"Hermes native Anthropic request does not preserve {effort} effort")
        if any(key in kwargs or key in kwargs.get("extra_body", {}) for key in ("temperature", "top_p", "top_k")):
            raise RuntimeError("Hermes sends sampling parameters rejected by Claude Haiku 5.5")
        if kwargs.get("tool_choice", {}).get("disable_parallel_tool_use") is not True:
            raise RuntimeError("Hermes does not disable native Anthropic parallel tool use")
        if kwargs.get("max_tokens") != 128000:
            raise RuntimeError("Hermes native Haiku 5.5 default output limit is not 128000")
        requests[effort] = {key: kwargs[key] for key in ("model", "max_tokens", "thinking", "output_config", "tool_choice")}

    messages = [{"role": "user", "content": "First question."}]
    for label in ("first", "second"):
        messages.extend([
            {"role": "assistant", "content": f"{label} answer", "reasoning_details": [
                {"type": "thinking", "thinking": f"{label} thinking", "signature": f"probe-{label}"}]},
            {"role": "user", "content": f"Continue after {label}."},
        ])
    converted = adapter.build_anthropic_kwargs(
        model=MODEL, messages=messages, tools=None, max_tokens=16384,
        reasoning_config={"enabled": True, "effort": "medium"},
        is_oauth=False, context_length=131072, base_url="https://api.anthropic.com",
    )
    thinking = [block for message in converted["messages"] for block in message["content"]
                if isinstance(block, dict) and block.get("type") == "thinking"]
    if not policy.model_preserves_prior_thinking(MODEL) or [(item.get("thinking"), item.get("signature")) for item in thinking] != [("first thinking", "probe-first"), ("second thinking", "probe-second")]:
        raise RuntimeError("Hermes does not replay Haiku 5.5 prior thinking blocks unchanged")
    return {"requests": requests, "prior_thinking_replay_verified": True,
            "parallel_tool_use_disabled": True, "default_max_output_tokens": 128000,
            "verification_scope": "local native request builder; no API request sent"}


def provenance(root):
    names = ("agent/anthropic_adapter.py", "agent/anthropic_thinking_policy.py",
             "agent/anthropic_message_convert.py", "hermes_cli/main.py", "hermes_bootstrap.py", "pm/environments.py")
    hashes = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names}
    try:
        commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL, timeout=5).strip()
    except (OSError, subprocess.SubprocessError):
        commit = None
    dependency = dict(_DEPENDENCY_CONTEXT)
    if dependency.get("hermes_dependency_state"):
        facts = Path(dependency["hermes_dependency_state"]) / "facts.json"
        dependency["hermes_dependency_facts_sha256"] = hashlib.sha256(facts.read_bytes()).hexdigest()
    return {**dependency, **_SDK_CONTEXT, "hermes_root": str(root), "hermes_python": sys.executable,
            "hermes_commit": commit, "hermes_source_hashes": hashes,
            "compatibility_wrapper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


def verify_runtime_proof(root, proof_path):
    """Refuse runtime drift before any model call in a resumed or long batch."""
    expected = json.loads(Path(proof_path).read_text())
    actual = provenance(root)
    if not isinstance(expected, dict) or any(expected.get(key) != value for key, value in actual.items()):
        raise RuntimeError("Hermes runtime or compatibility wrapper changed since batch preflight; start a new batch")


def main(argv=None):
    # Forward --help to Hermes, including `chat --help` used by the evaluator.
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser.add_argument("--hermes-root", required=True, type=Path)
    parser.add_argument("--check", action="store_true", help="Print native request compatibility and provenance without an API call")
    # Profile selection is consumed by the normal launcher before Hermes main.
    # This evaluator supplies an explicit fresh HERMES_HOME and uses default only.
    parser.add_argument("--profile", choices=("default",), help=argparse.SUPPRESS)
    args, remaining = parser.parse_known_args(argv)
    root = args.hermes_root.expanduser().resolve()
    if not (root / "hermes_cli/main.py").is_file():
        parser.error(f"Hermes installation missing at {root}")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    sys._hermes_pin_default_home = True
    # Evaluation never repairs or updates the user's installed dependency set.
    os.environ["HERMES_DISABLE_LAZY_INSTALLS"] = "1"
    # Bootstrap classifies Hermes arguments when activating its dependency runtime.
    # Keep this wrapper's private flags out of that classification.
    sys.argv = ["hermes", *(remaining if not args.check else ["--version"])]
    try:
        bind_installed_dependencies(root)
        require_healthy_install(root)
        proof_path = os.environ.get("HERMES_EVAL_RUNTIME_PROOF")
        if proof_path:
            verify_runtime_proof(root, proof_path)
        import hermes_bootstrap  # noqa: F401: activate the installed Hermes runtime
        sdk_directory = os.environ.get("HERMES_EVAL_SDK_DIR")
        if sdk_directory:
            configure_local_sdk(sdk_directory)
        # Check the SDK tree after activation as well as the installed runtime.
        if proof_path:
            verify_runtime_proof(root, proof_path)
        if sdk_directory:
            import_local_sdk()
        from agent import anthropic_adapter as adapter
        from agent import anthropic_thinking_policy as policy
        from agent import anthropic_message_convert as converter
        required = install_compatibility(adapter, policy, converter)
        checked = probe(adapter, policy)
        if args.check:
            if remaining:
                parser.error("--check does not accept Hermes command arguments")
            print(json.dumps({**provenance(root), **checked, "compatibility_required": required}, sort_keys=True))
            return 0
        from hermes_cli.main import main as hermes_main
        sys.argv = ["hermes", *remaining]
        return hermes_main()
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        print(f"Haiku Hermes compatibility error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
