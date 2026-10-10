#!/usr/bin/env bash
# Setup Muse Glimmer on llama.cpp server
# Based on Meta official docs: https://dev.meta.ai/docs/muse-glimmer/llama-cpp
# and Unsloth guide

set -euo pipefail

# Configurable
MODEL_DIR="${MODEL_DIR:-./muse-glimmer}"
LLAMA_DIR="${LLAMA_DIR:-./llama.cpp}"
MODEL_NAME="Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf"
MMPROJ_NAME="mmproj-Muse-Glimmer-30B-Q4_K_M.gguf"
PORT="${PORT:-8080}"
HOST="${HOST:-127.0.0.1}"
API_KEY="${glimmerapikey:-fwewfw234fesef}"
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

# Resolve paths against the current working directory so later cd steps do not break the model paths.
case "$MODEL_DIR" in
  /*) ;; 
  *) MODEL_DIR="$PWD/$MODEL_DIR" ;;
esac
case "$LLAMA_DIR" in
  /*) ;; 
  *) LLAMA_DIR="$PWD/$LLAMA_DIR" ;;
esac

mkdir -p "$MODEL_DIR" "$LLAMA_DIR"

echo "[1/5] Installing build dependencies..."
apt-get update -qq
apt-get install -y -qq git cmake build-essential curl libcurl4-openssl-dev

echo "[2/5] Cloning llama.cpp..."
if [ ! -d "$LLAMA_DIR/.git" ]; then
  git clone https://github.com/ggml-org/llama.cpp "$LLAMA_DIR"
fi
cd "$LLAMA_DIR"
git fetch --tags
# Pin to a version with Muse Glimmer support (b10353+)
git checkout b10353 || git checkout main

echo "[3/5] Building llama.cpp..."
cmake -B build -DCMAKE_BUILD_TYPE=Release -DLLAMA_BUILD_UI=OFF -DLLAMA_USE_PREBUILT_UI=OFF \
  -DGGML_CUDA=ON -DGGML_NATIVE=OFF -DCMAKE_CUDA_ARCHITECTURES=90 2>/dev/null || \
cmake -B build -DCMAKE_BUILD_TYPE=Release -DLLAMA_BUILD_UI=OFF -DLLAMA_USE_PREBUILT_UI=OFF
cmake --build build -j"$(nproc)" --target llama-server llama-cli llama-mtmd-cli

# Verify Muse Glimmer arch support
if ! grep -q LLM_ARCH_MUSE_GLIMMER src/llama-arch.cpp; then
  echo "ERROR: Muse Glimmer not supported in this checkout"
  exit 1
fi

echo "[4/5] Downloading Muse Glimmer GGUF checkpoints..."
python3 -m pip install -U "huggingface_hub[cli]"
if command -v hf >/dev/null 2>&1; then
  HF_CLI=(hf)
elif command -v huggingface-cli >/dev/null 2>&1; then
  HF_CLI=(huggingface-cli)
else
  echo "ERROR: Hugging Face CLI is not available after install."
  exit 1
fi
"${HF_CLI[@]}" download meta-models/Muse-Glimmer-30B-GGUF --local-dir "$MODEL_DIR" \
  --include "Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf" \
  --include "mmproj-Muse-Glimmer-30B-Q4_K_M.gguf"

# Ensure context length metadata is correct
MODEL_PATH="$MODEL_DIR/$MODEL_NAME"
if command -v python3 >/dev/null; then
  python3 "$LLAMA_DIR/gguf-py/gguf/scripts/gguf_set_metadata.py" "$MODEL_PATH" muse-glimmer.context_length 131072 || true
fi

echo "[5/5] Starting llama.cpp server..."
cd "$LLAMA_DIR"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/muse-glimmer-$HOST-$PORT-$(date +%Y%m%d-%H%M%S).log"
echo "Using host $HOST port $PORT"
echo "Logs: $LOG_FILE"
nohup ./build/bin/llama-server \
  -m "$MODEL_PATH" \
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
