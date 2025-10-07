# Airos Voice Agent Framework
> Local-first, privacy-preserving **voice AI** with portable memory — built on **Dora** dataflow.

Airos Voice Agent is an open, modular framework for building private assistants that run on **client devices** (laptops/phones) and **edge nodes**, with **cloud** as a complement when needed.

- 🎙️ **Voice-first** UX: VAD, wake word, streaming ASR/TTS, barge-in  
- 🧠 **Portable, private memory**: local vector store for user context (opt-in sync)  
- 🧭 **Hybrid routing**: local → edge → cloud LLMs via a **smart LLM router**  
- 🔌 **Dora** dataflow runtime: composable graphs, production-friendly

_Reference inspirations_: OpenAI Realtime, Vapi voice agents, Dora examples:  
`examples/mac-aec-chat`, `examples/chatbot-openai-0905`, `examples/chatbot-openai-websocket-browser` from the Dora repo branch `cloud-model-mcp` (https://github.com/kippalbot/dora/tree/cloud-model-mcp).

---

## Why this framework?

- **Sovereign AI** — your data stays on your device by default; edge/cloud only by policy.  
- **Voice done right** — low-latency turns, duplex audio, robust VAD and interruption.  
- **Composable** — swap ASR/TTS/LLM backends; run the same graphs locally or at the edge.  
- **Operational** — metrics, logs, and guardrails are first-class.

---

## Three-Tier Strategy (high-level)

```
┌─────────────────────────────────────────────┐
│  Tier 1: Local (fast, private)              │
│  ├─ ASR: Whisper/FunASR (tiny/int8)         │
│  ├─ LLM: MLX (Apple Silicon) / llama.cpp    │
│  └─ TTS: PrimeSpeech/Coqui (local)          │
├─────────────────────────────────────────────┤
│  Tier 2: Edge (balanced)                    │
│  ├─ Local ASR → Edge/Cloud LLM → Local TTS  │
│  └─ Smart caching & prefetch                │
├─────────────────────────────────────────────┤
│  Tier 3: Cloud (full capability)            │
│  └─ OpenAI/Qwen/Anthropic via MCP/vLLM      │
└─────────────────────────────────────────────┘
```

---

## Repository Layout (proposed)

```
airos-voice-agent/
├── README.md
├── ARCHITECTURE.md
├── core/                     # Dora graphs
│   ├── dataflow-local.yml    # Mic → ASR → Router(local) → TTS
│   ├── dataflow-hybrid.yml   # Local ASR/TTS + cloud LLM
│   ├── dataflow-cloud.yml    # Full cloud pipeline
│   └── dataflow-server.yml   # WebSocket server + static nodes
├── nodes/
│   ├── audio-input/          # Mac AEC + cross-platform handlers
│   ├── audio-output/         # Player/streamer
│   ├── vad/                  # dora-speechmonitor / WebRTC VAD
│   ├── asr/                  # Whisper/FunASR runners
│   ├── tts/                  # PrimeSpeech/Coqui runners
│   ├── llm-router/           # Smart routing (local/edge/cloud)
│   ├── memory/               # Local vector DB + policy
│   └── monitoring/           # viewer/metrics
├── configs/
│   ├── local.toml
│   ├── cloud-openai.toml
│   ├── cloud-alicloud.toml
│   └── routing-rules.toml
├── examples/
│   ├── quickstart-local.md
│   ├── quickstart-hybrid.md
│   └── server-deployment.md
└── scripts/
    ├── setup-local.sh
    ├── setup-cloud.sh
    └── benchmark.py
```

---

## MVP Scope (v1.0)

- ✅ Local pipeline: **Mic → VAD → ASR → LLM(local) → TTS**, push-to-talk  
- ✅ Config-switch to **cloud LLM** (OpenAI/Qwen) with local ASR/TTS  
- ✅ Local memory (vector DB) for short-term session + opt-in long-term  
- ✅ Basic metrics/logs; CLI runner  
- ❌ Smart router (auto) → **v1.1**  
- ❌ WebSocket multi-client server → **v1.2**  
- ❌ Cross-platform audio (Pulse/WASAPI) → **v2.0**  

---

## Getting Started (skeleton)

```bash
# Local dev
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run a local graph
dora up core/dataflow-local.yml

# Switch to hybrid
dora up core/dataflow-hybrid.yml
```

---

## References

- Dora dataflow (branch `cloud-model-mcp`): https://github.com/kippalbot/dora/tree/cloud-model-mcp  
- Vapi voice agents (concepts): https://docs.vapi.ai/quickstart/introduction  
- OpenAI Realtime (concepts/UX)

---

## License

Apache-2.0 (TBD)
