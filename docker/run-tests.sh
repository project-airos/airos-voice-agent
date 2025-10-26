#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_DIR="$SCRIPT_DIR"
ENV_FILE_DEFAULT="$COMPOSE_DIR/.env"

SKIP_BUILD=0
FORCE_REBUILD=0
RUN_ARGS=()
HOST_OUTPUT_DIR=""

usage() {
  cat <<USAGE
Usage: $(basename "$0") [options] [-- <smoke-test args>]

Options:
  --asr             Run only the ASR smoke test inside the container
  --tts             Run only the TTS smoke test inside the container
  --output-dir DIR  Persist synthesized audio to DIR on the host
  --skip-build      Skip automatic docker image build (assumes image exists)
  --rebuild         Force rebuild of the docker image before testing
  -h, --help        Show this help message

All unrecognized arguments after "--" are passed directly to the smoke test
script inside the container.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --asr|--tts)
      RUN_ARGS+=("$1")
      shift
      ;;
    --output-dir)
      if [[ $# -lt 2 ]]; then
        echo "Error: --output-dir requires a directory argument" >&2
        exit 1
      fi
      HOST_OUTPUT_DIR="$2"
      shift 2
      ;;
    --skip-build)
      SKIP_BUILD=1
      shift
      ;;
    --rebuild)
      FORCE_REBUILD=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      RUN_ARGS+=("$@")
      break
      ;;
    *)
      echo "Error: Unknown option $1" >&2
      usage
      exit 1
      ;;
  esac
done

# Load environment variables from docker/.env if present to resolve MODELS_DIR.
ENV_FILE_PATH="${ENV_FILE:-$ENV_FILE_DEFAULT}"
if [[ -f "$ENV_FILE_PATH" ]]; then
  set -a
  source "$ENV_FILE_PATH"
  set +a
fi

: "${MODELS_DIR:?MODELS_DIR must be set in docker/.env or the environment}"

if [[ ! -d "$MODELS_DIR" ]]; then
  echo "Warning: MODELS_DIR ($MODELS_DIR) does not exist. The smoke tests may fail if models are missing." >&2
fi

IMAGE_TAG="${IMAGE_TAG:-latest}"
IMAGE_NAME="airos-voice-agent:$IMAGE_TAG"

if [[ $FORCE_REBUILD -eq 1 ]]; then
  echo "🔁 Forcing docker image rebuild..."
  "$PROJECT_ROOT/scripts/build-docker.sh"
elif [[ $SKIP_BUILD -eq 0 ]]; then
  if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    echo "📦 Docker image $IMAGE_NAME not found. Building it now..."
    "$PROJECT_ROOT/scripts/build-docker.sh"
  fi
fi

cd "$COMPOSE_DIR"

COMPOSE_CMD=(docker compose run --rm)

if [[ -n "$HOST_OUTPUT_DIR" ]]; then
  HOST_OUTPUT_ABS="$(cd "$PROJECT_ROOT" && python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$HOST_OUTPUT_DIR")"
  mkdir -p "$HOST_OUTPUT_ABS"
  COMPOSE_CMD+=(--volume "$HOST_OUTPUT_ABS:/artifacts")
  RUN_ARGS+=("--output-dir" "/artifacts")
fi

COMPOSE_CMD+=(tests)

if [[ ${#RUN_ARGS[@]} -gt 0 ]]; then
  COMPOSE_CMD+=("${RUN_ARGS[@]}")
fi

echo "🚀 Running smoke tests inside container..."
printf '  %s\n' "${COMPOSE_CMD[@]}"

"${COMPOSE_CMD[@]}"
