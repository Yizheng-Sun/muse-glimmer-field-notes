#!/usr/bin/env bash
# Share the existing credential prompt, detached startup and log preservation.
set -euo pipefail
TASK_REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export EVAL_DEFAULT_CONFIG="$TASK_REPO_ROOT/config/evaluation-daily.json"
export EVAL_EXPECT_PROVIDER=glimmer
export EVAL_RUNNER_SCRIPT=scripts/evaluate_daily.py
export EVAL_LAUNCH_NAME=daily-evaluation
export EVAL_BATCH_NAMESPACE=daily-evaluation
exec bash "$TASK_REPO_ROOT/scripts/run_evaluation.sh" "$@"
