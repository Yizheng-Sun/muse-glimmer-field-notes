#!/usr/bin/env bash
set -euo pipefail

MODEL_DIR="${MODEL_DIR:-/workspace/muse-glimmer-field-notes/muse-glimmer}"
LLAMA_DIR="${LLAMA_DIR:-/workspace/muse-glimmer-field-notes/llama.cpp}"
MODEL_NAME="Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf"
MMPROJ_NAME="mmproj-Muse-Glimmer-30B-Q4_K_M.gguf"
PORT="${PORT:-8080}"
HOST="${HOST:-127.0.0.1}"
API_KEY="glimmerapikey:-fwewfw234fesef"
REASONING_STRENGTH="${REASONING_STRENGTH:-low}"
LOG_DIR="${LOG_DIR:-$PWD/.logs}"

choose_free_port() {
  local host="$1"
  local port="$2"
  local candidate="$port"
  local max_port=$((port + 20))

  while [ "$candidate" -le "$max_port" ]; do
    if python3 - "$host" "$candidate" <<'PY'
import socket, sys
host, port = sys.argv[1], int(sys.argv[2])
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    s.bind((host, port))
except OSError:
    raise SystemExit(1)
else:
    raise SystemExit(0)
finally:
    s.close()
PY
    then
      printf '%s\n' "$candidate"
      return 0
    fi
    candidate=$((candidate + 1))
  done

  echo "ERROR: no free port found for $host from $port to $max_port" >&2
  return 1
}

PORT="$(choose_free_port "$HOST" "$PORT")"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/muse-glimmer-$HOST-$PORT-$(date +%Y%m%d-%H%M%S).log"

if [ ! -f "$LLAMA_DIR/build/bin/llama-server" ]; then
  echo "ERROR: llama-server not found at $LLAMA_DIR/build/bin/llama-server"
  echo "Run setup_muse_glimmer_llama.sh first or set LLAMA_DIR to the correct build directory."
  exit 1
fi

if [ ! -f "$MODEL_DIR/$MODEL_NAME" ]; then
  echo "ERROR: model file not found at $MODEL_DIR/$MODEL_NAME"
  exit 1
fi

if [ ! -f "$MODEL_DIR/$MMPROJ_NAME" ]; then
  echo "ERROR: mmproj file not found at $MODEL_DIR/$MMPROJ_NAME"
  exit 1
fi

cd "$LLAMA_DIR"
nohup ./build/bin/llama-server \
  -m "$MODEL_DIR/$MODEL_NAME" \
  --mmproj "$MODEL_DIR/$MMPROJ_NAME" \
  -a muse-glimmer \
  -ngl 99 -c 131072 -np 1 \
  --host "$HOST" --port "$PORT" --api-key "$API_KEY" \
  --jinja \
  --chat-template-kwargs "{\"reasoning_strength\":\"$REASONING_STRENGTH\"}" \
  >"$LOG_FILE" 2>&1 &

SERVER_PID=$!
echo "$SERVER_PID" > "$LOG_DIR/muse-glimmer.pid"

echo "Server started at http://$HOST:$PORT"
echo "PID: $SERVER_PID"
echo "Log: $LOG_FILE"


