#############################
# Airos Voice Agent - Docker Image
# Based on Dora voice chat examples
#############################

#############################
# Builder: Rust binaries
#############################
FROM rust:1.85-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates pkg-config libssl-dev build-essential git \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /src

# Clone Dora repo for building required Rust components
# Note: You may want to pin to a specific commit/tag for production
RUN git clone --depth 1 --branch cloud-model-mcp https://github.com/kippalbot/dora.git /src/dora

WORKDIR /src/dora

# Build the WebSocket server and MaaS client
RUN cargo build --release -p dora-openai-websocket \
 && cargo build --release -p dora-maas-client \
 && cargo install --path binaries/cli --locked

#############################
# Runtime: Python + system deps
#############################
FROM python:3.12-slim AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8123 \
    PIP_NO_CACHE_DIR=1

# System libs for audio/ML and dev tooling
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    build-essential pkg-config \
    libopenblas-dev openssl libssl-dev \
    portaudio19-dev libsndfile1 libgomp1 libomp-dev \
    ffmpeg \
    git \
    nodejs npm \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /opt/airos

# Copy airos-voice-agent repo content
COPY . /opt/airos/

# Copy Dora node-hub components we need
COPY --from=builder /src/dora/node-hub/dora-asr /opt/airos/nodes/dora-asr
COPY --from=builder /src/dora/node-hub/dora-primespeech /opt/airos/nodes/dora-primespeech
COPY --from=builder /src/dora/node-hub/dora-speechmonitor /opt/airos/nodes/dora-speechmonitor
COPY --from=builder /src/dora/node-hub/dora-text-segmenter /opt/airos/nodes/dora-text-segmenter

# Copy built Rust binaries
COPY --from=builder /src/dora/target/release/dora-openai-websocket /usr/local/bin/dora-openai-websocket
COPY --from=builder /src/dora/target/release/dora-maas-client /usr/local/bin/dora-maas-client
COPY --from=builder /usr/local/cargo/bin/dora /usr/local/bin/dora

# Python deps (CPU-only torch; adjust if you add CUDA)
RUN pip install --no-cache-dir --upgrade pip wheel setuptools \
 && pip install --no-cache-dir numpy==1.26.4 \
 && pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
      torch==2.2.0 torchvision==0.17.0 torchaudio==2.2.0 \
 && pip install --no-cache-dir pyaudio sounddevice \
 && pip install --no-cache-dir funasr-onnx onnxruntime onnxruntime-extensions

# Install core dependencies from requirements
COPY docker/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Install MCP servers and Playwright for browser automation
RUN npm i -g @playwright/mcp @modelcontextprotocol/server-filesystem \
 && npx --yes playwright install --with-deps chromium

# Install pywhispercpp from GitHub
RUN pip install --no-cache-dir "git+https://github.com/absadiki/pywhispercpp.git"

# Optional: JupyterLab for in-container debugging
RUN pip install --no-cache-dir jupyterlab

# Sanity check core ASR deps
RUN python - <<'PY'
try:
    import funasr_onnx, onnxruntime as ort
    print('✅ funasr_onnx:', getattr(funasr_onnx, '__version__', 'unknown'))
    print('✅ onnxruntime providers:', ort.get_available_providers())
except Exception as e:
    print('⚠️ funasr_onnx/onnxruntime import issue:', e)
try:
    import pywhispercpp
    print('✅ pywhispercpp OK')
except Exception as e:
    print('⚠️ pywhispercpp import issue:', e)
PY

# Install Dora Python nodes (editable mode)
RUN pip install -e nodes/dora-asr --no-deps \
               -e nodes/dora-primespeech --no-deps \
               -e nodes/dora-speechmonitor --no-deps \
               -e nodes/dora-text-segmenter --no-deps || true

# Model directory volume
VOLUME ["/root/.dora/models"]

# Working directory for examples
WORKDIR /opt/airos/examples/openai-realtime

# Expose WebSocket port
EXPOSE 8123

# Entrypoint script
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

CMD ["/usr/local/bin/entrypoint.sh"]
