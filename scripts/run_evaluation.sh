#!/usr/bin/env bash
# Launch the coding matrix on the machine hosting Muse Glimmer.
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

EVAL_PYTHON=""
for candidate in "${CASE_PYTHON:-}" python3 python3.12 python3.13 python3.14; do
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

# Inspection stays in the foreground and never asks for a credential.
for argument in "$@"; do
  case "$argument" in
    --dry-run|--help|-h)
      exec "$EVAL_PYTHON" -u scripts/evaluate_coding.py "$@"
      ;;
  esac
done

"$EVAL_PYTHON" -c 'import venv, pip' || {
  echo 'The selected Python needs venv and pip before evaluation can run.' >&2
  exit 2
}
# Validate the matrix before starting a detached process.
matrix="$("$EVAL_PYTHON" scripts/evaluate_coding.py --dry-run "$@")"
printf '%s\n' "${matrix%%$'\n'*}"

# A resumed batch takes its credential-variable name from its frozen config.
key_env="$("$EVAL_PYTHON" - "$@" <<'PY'
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--config', type=Path, default=Path('config/evaluation.json'))
parser.add_argument('--resume', type=Path)
args, _ = parser.parse_known_args()
path = args.resume / 'config.json' if args.resume else args.config
print(json.loads(path.read_text())['api_key_env'])
PY
)"

mkdir -p .runs
pid_file="$REPO_ROOT/.runs/evaluation-launch.pid"
if [ -f "$pid_file" ]; then
  previous_pid="$(cat "$pid_file")"
  if [[ "$previous_pid" =~ ^[1-9][0-9]*$ ]] && kill -0 "$previous_pid" 2>/dev/null; then
    echo "An evaluation is already running (PID $previous_pid). Follow .runs/evaluation-launch.log." >&2
    exit 2
  fi
fi

# Serialize startup; the PID file guards the batch after this short lock ends.
launch_lock="$REPO_ROOT/.runs/.evaluation-launch-lock"
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
  key="${GLIMMER_API_KEY:-${glimmerapikey:-}}"
fi
if [ -z "$key" ]; then
  if [ -t 0 ]; then
    read -r -s -p 'Muse Glimmer server API key (Enter if authentication is disabled): ' key
    printf '\n'
  else
    echo "Set $key_env to the server API key before a noninteractive launch; use local-no-auth if authentication is disabled." >&2
    exit 2
  fi
fi
printf -v "$key_env" '%s' "${key:-local-no-auth}"
export "$key_env"
unset key

stamp="$(date -u +%Y%m%dT%H%M%SZ)-$$"
log_file="$REPO_ROOT/.runs/evaluation-launch-$stamp.log"
latest_log="$REPO_ROOT/.runs/evaluation-launch.log"
# Preserve logs from the earlier manual launch command, too.
if [ -f "$latest_log" ] && [ ! -L "$latest_log" ]; then
  mv "$latest_log" "$REPO_ROOT/.runs/evaluation-launch-before-$stamp.log"
fi
ln -sfn "$(basename "$log_file")" "$latest_log"
nohup "$EVAL_PYTHON" -u "$REPO_ROOT/scripts/evaluate_coding.py" "$@" \
  > "$log_file" 2>&1 < /dev/null &
evaluation_pid=$!
printf '%s\n' "$evaluation_pid" > "$pid_file"

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
printf 'Evaluation launched in the background (PID %s). You can disconnect from SSH.\n' "$evaluation_pid"
printf 'Python: %s\nLog: %s\n' "$EVAL_PYTHON" "$log_file"
printf 'Watch: tail -f "%s"\n' "$latest_log"
printf 'The log records setup checks, progress, and the batch path under .runs/evaluation/.\n'
