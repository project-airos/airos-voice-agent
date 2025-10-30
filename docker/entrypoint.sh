#!/bin/bash
set -euo pipefail

echo "[airos] Starting Airos Voice Agent..."

echo "[airos] Cleaning Dora state..."
dora destroy || true

echo "[airos] Starting Dora daemon..."
dora up

echo "[airos] Waiting for Dora to be ready..."
for i in $(seq 1 30); do
  if dora list >/dev/null 2>&1; then
    echo "[airos] ✅ Dora is ready."
    break
  fi
  sleep 0.5
done

# Configuration with defaults
EXAMPLE_DIR="${EXAMPLE_DIR:-/opt/airos}"
DATAFLOW_FILE="${DATAFLOW_FILE:-dataflow.yml}"
DATAFLOW_NAME="${DATAFLOW_NAME:-voice-agent}"
WS_SERVER_NAME="${WS_SERVER_NAME:-wserver}"

echo "[airos] Using example dir: ${EXAMPLE_DIR}"
cd "${EXAMPLE_DIR}" || { echo "[airos] ❌ Cannot cd into ${EXAMPLE_DIR}"; exit 1; }

# Auto-create config from example if needed
DEFAULT_CONFIG="maas_config.toml"
if [ ! -f "$DEFAULT_CONFIG" ] && [ -f "${DEFAULT_CONFIG}.example" ]; then
  echo "[airos] Creating $DEFAULT_CONFIG from example..."
  cp "${DEFAULT_CONFIG}.example" "$DEFAULT_CONFIG"
fi

# Build and start dataflow if present
if [ -f "${DATAFLOW_FILE}" ]; then
  if [ "${SKIP_DORA_BUILD:-0}" = "1" ]; then
    echo "[airos] Skipping dora build (SKIP_DORA_BUILD=1)"
  else
    echo "[airos] Building dataflow: ${DATAFLOW_FILE}"
    dora build "${DATAFLOW_FILE}"
  fi

  echo "[airos] Starting dataflow: ${DATAFLOW_FILE} (name: ${DATAFLOW_NAME})"
  dora start "${DATAFLOW_FILE}" --name "${DATAFLOW_NAME}" --detach

  # Give daemon time to register nodes so dynamic connections succeed
  sleep 1

  # Tail node logs if requested (runs in background)
  if [ -n "${TAIL_NODE_LOGS:-}" ]; then
    for NODE in $(echo "$TAIL_NODE_LOGS" | tr ',' ' '); do
      echo "[airos] Tailing logs for node: $NODE"
      env NODE="$NODE" DATAFLOW_NAME="$DATAFLOW_NAME" bash -c '
        while :; do
          if dora logs "$DATAFLOW_NAME" "$NODE" 2>/dev/null | sed -u "s/^/[$NODE] /"; then
            echo "[airos] Log stream ended for $NODE, retrying..." >&2
          else
            echo "[airos] Waiting for $NODE logs..." >&2
          fi
          sleep 1
        done
      ' &
    done
  fi

  echo "[airos] ✅ Dataflow started. Launching WebSocket server..."
  echo "[airos] 🚀 WebSocket server on ${HOST:-0.0.0.0}:${PORT:-8123}"

  # Launch WebSocket server as dynamic node (connects to dataflow)
  exec dora-openai-websocket -- --name "${WS_SERVER_NAME}"
else
  echo "[airos] No ${DATAFLOW_FILE} found, skipping dataflow start"
fi
