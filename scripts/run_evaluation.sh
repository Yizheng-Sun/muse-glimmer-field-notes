#!/usr/bin/env bash
# Launch the coding matrix with private credentials and a detached process.
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

EVAL_PYTHON=""
for candidate in "${CASE_PYTHON:-}" python3 python3.12 python3.13 python3.14 \
  "${HOME:-}/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"; do
  [ -n "$candidate" ] || continue
  if resolved="$("$candidate" -c 'import sys; assert sys.version_info >= (3, 12); print(sys.executable)' 2>/dev/null)"; then
    EVAL_PYTHON="$resolved"
    break
  fi
done
if [ -z "$EVAL_PYTHON" ]; then
  echo 'Python 3.12+ is required. Set CASE_PYTHON to its interpreter path.' >&2
  exit 2
fi

if [ -n "${EVAL_DEFAULT_CONFIG:-}" ]; then
  # argparse accepts the final --config, so an explicit override wins.
  set -- --config "$EVAL_DEFAULT_CONFIG" "$@"
fi

runner_script="${EVAL_RUNNER_SCRIPT:-scripts/evaluate_coding.py}"
case "$runner_script" in
  scripts/evaluate_coding.py|scripts/evaluate_daily.py) ;;
  *) echo 'Unsupported evaluation runner.' >&2; exit 2 ;;
esac

# Inspection stays in the foreground and never asks for a credential.
for argument in "$@"; do
  case "$argument" in
    --dry-run|--help|-h)
      exec "$EVAL_PYTHON" -u "$runner_script" "$@"
      ;;
    --prepare-only)
      if [ "$runner_script" = scripts/evaluate_daily.py ]; then
        exec "$EVAL_PYTHON" -u "$runner_script" "$@"
      fi
      ;;
  esac
done

if [ "$runner_script" = scripts/evaluate_coding.py ]; then
  "$EVAL_PYTHON" -c 'import venv, pip' || {
    echo 'The selected Python needs venv and pip before evaluation can run.' >&2
    exit 2
  }
fi
# Validate the matrix before starting a detached process.
matrix="$("$EVAL_PYTHON" "$runner_script" --dry-run "$@")"
printf '%s\n' "${matrix%%$'\n'*}"

# A resumed batch takes its credential-variable name from its frozen config.
launch_settings="$("$EVAL_PYTHON" - "$@" <<'PY'
import argparse
import json
import os
import re
import shutil
from pathlib import Path

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--config', type=Path, default=Path('config/evaluation.json'))
parser.add_argument('--resume', type=Path)
args, _ = parser.parse_known_args()
path = args.resume / 'config.json' if args.resume else args.config
config = json.loads(path.read_text())
provider = config.get('provider', 'glimmer')
expected = os.environ.get('EVAL_EXPECT_PROVIDER')
if expected and provider != expected:
    parser.error(f'This launcher requires provider={expected}; {path} uses provider={provider}.')
key_env = config['api_key_env']
if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key_env):
    parser.error('api_key_env must be a valid environment-variable name.')
if provider == 'anthropic':
    command = config.get('hermes_command', ['hermes'])[0]
    if not shutil.which(command):
        parser.error('Hermes is required on this Mac. Install it and make hermes available in PATH before launching.')
print(key_env)
print(provider)
PY
)"
key_env="${launch_settings%%$'\n'*}"
provider="${launch_settings##*$'\n'}"
launch_name="${EVAL_LAUNCH_NAME:-evaluation}"
if [[ ! "$launch_name" =~ ^[a-z][a-z0-9-]*$ ]]; then
  echo 'EVAL_LAUNCH_NAME must contain lowercase letters, digits, or hyphens.' >&2
  exit 2
fi

mkdir -p .runs
pid_file="$REPO_ROOT/.runs/$launch_name-launch.pid"
if [ -f "$pid_file" ]; then
  previous_pid="$(cat "$pid_file")"
  if [[ "$previous_pid" =~ ^[1-9][0-9]*$ ]] && kill -0 "$previous_pid" 2>/dev/null; then
    echo "An evaluation is already running (PID $previous_pid). Follow .runs/$launch_name-launch.log." >&2
    exit 2
  fi
fi

# Serialize startup; the PID file guards the batch after this short lock ends.
launch_lock="$REPO_ROOT/.runs/.$launch_name-launch-lock"
if ! mkdir "$launch_lock" 2>/dev/null; then
  echo "Another launcher owns $launch_lock. If it stopped unexpectedly, remove that directory and retry." >&2
  exit 2
fi
trap 'rmdir "$launch_lock"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP
if [ -f "$pid_file" ]; then
  previous_pid="$(cat "$pid_file")"
  if [[ "$previous_pid" =~ ^[1-9][0-9]*$ ]] && kill -0 "$previous_pid" 2>/dev/null; then
    echo "An evaluation is already running (PID $previous_pid)." >&2
    exit 2
  fi
fi

key="${!key_env:-}"
if [ -z "$key" ]; then
  if [ "$provider" != anthropic ]; then
    key="${GLIMMER_API_KEY:-${glimmerapikey:-}}"
  fi
fi
if [ -z "$key" ]; then
  if [ -t 0 ]; then
    if [ "$provider" = anthropic ]; then
      read -r -s -p 'Anthropic API key (required): ' key
    else
      read -r -s -p 'Muse Glimmer server API key (Enter if authentication is disabled): ' key
    fi
    printf '\n'
  else
    if [ "$provider" = anthropic ]; then
      echo "Set $key_env to your Anthropic API key before a noninteractive launch." >&2
    else
      echo "Set $key_env to the server API key before a noninteractive launch; use local-no-auth if authentication is disabled." >&2
    fi
    exit 2
  fi
fi
if [ "$provider" = anthropic ] && [ -z "$key" ]; then
  echo "An Anthropic API key is required. Set $key_env or enter it at the private prompt." >&2
  exit 2
fi
printf -v "$key_env" '%s' "${key:-local-no-auth}"
export "$key_env"
unset key

stamp="$(date -u +%Y%m%dT%H%M%SZ)-$$"
log_file="$REPO_ROOT/.runs/$launch_name-launch-$stamp.log"
latest_log="$REPO_ROOT/.runs/$launch_name-launch.log"
# Preserve logs from the earlier manual launch command, too.
if [ -f "$latest_log" ] && [ ! -L "$latest_log" ]; then
  mv "$latest_log" "$REPO_ROOT/.runs/$launch_name-launch-before-$stamp.log"
fi
ln -sfn "$(basename "$log_file")" "$latest_log"
nohup "$EVAL_PYTHON" -u "$REPO_ROOT/$runner_script" "$@" \
  > "$log_file" 2>&1 < /dev/null &
evaluation_pid=$!
printf '%s\n' "$evaluation_pid" > "$pid_file"
if [ "$provider" = anthropic ] && [ "$(uname -s)" = Darwin ] && command -v caffeinate >/dev/null 2>&1; then
  # Watch the actual evaluator PID, so its PID file still supports stopping it.
  nohup caffeinate -i -w "$evaluation_pid" > /dev/null 2>&1 < /dev/null &
fi

sleep 1
if ! kill -0 "$evaluation_pid" 2>/dev/null; then
  if wait "$evaluation_pid"; then
    printf 'Evaluation finished. Log: %s\n' "$log_file"
    exit 0
  else
    status=$?
    tail -n 20 "$log_file" >&2
    printf 'Evaluation stopped during startup (exit %s). Log: %s\n' "$status" "$log_file" >&2
    exit "$status"
  fi
fi
printf 'Evaluation launched in the background (PID %s).\n' "$evaluation_pid"
printf 'Python: %s\nLog: %s\n' "$EVAL_PYTHON" "$log_file"
printf 'Watch: tail -f "%s"\n' "$latest_log"
if [ "$provider" = anthropic ]; then
  printf 'The log records setup checks, progress, and the batch path under .runs/evaluation-haiku/.\n'
else
  printf 'The log records setup checks, progress, and the batch path under .runs/%s/.\n' "${EVAL_BATCH_NAMESPACE:-evaluation}"
fi
