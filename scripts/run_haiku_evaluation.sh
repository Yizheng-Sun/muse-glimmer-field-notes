#!/usr/bin/env bash
# Run the same coding matrix through Hermes and the Anthropic API on this Mac.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export EVAL_DEFAULT_CONFIG=config/evaluation-haiku.json
export EVAL_LAUNCH_NAME=haiku-evaluation
export EVAL_EXPECT_PROVIDER=anthropic
exec bash "$SCRIPT_DIR/run_evaluation.sh" "$@"
