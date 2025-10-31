# AI + MiniMax TTS Setup Guide

This guide explains how to use the new **AI-powered script generation with MiniMax cloud TTS** feature.

## 🎯 What's New

We've added a complete cloud-based podcast generation pipeline that combines:
- **AI Script Generation**: OpenAI or Anthropic LLMs automatically write podcast scripts
- **MiniMax TTS**: High-quality cloud text-to-speech (no local models needed)

This is the **fastest way to get started** - no model downloads required!

## 🚀 Quick Start

> 🔧 **One-time setup:** Build the project Docker image from the repo root:
> ```bash
> docker build --no-cache -t airos-voice-agent:latest -f docker/Dockerfile .
> ```

### Step 1: Set API Keys

```bash
# Required: Choose one LLM provider
export OPENAI_API_KEY=sk-your-openai-key
# OR
export ANTHROPIC_API_KEY=sk-ant-your-anthropic-key

# Required: MiniMax TTS
export MINIMAX_API_KEY=your-minimax-api-key
```

Prefer `.env`? Drop the same keys into `apps/podcast-generator/.env` (or the repo root `.env`) and `generate_podcast.sh` will load them automatically.

Get your keys from:
- OpenAI: https://platform.openai.com/api-keys
- Anthropic: https://console.anthropic.com/
- MiniMax: https://platform.minimax.io/user-center/basic-information/interface-key

### Step 2: Generate Your Podcast

```bash
# Basic usage (5-minute podcast with OpenAI + MiniMax)
./generate_podcast.sh "人工智能的未来" 5 openai output/ai_podcast.wav minimax

# 10-minute podcast with Anthropic + MiniMax
./generate_podcast.sh "区块链技术详解" 10 anthropic output/blockchain.wav minimax

# Custom output location
./generate_podcast.sh "量子计算简介" 7 openai output/quantum.wav minimax

# Chinese design topic with MiniMax cloud voices
./generate_podcast.sh "人工智能AIGC对艺术设计的影响及商业机会探讨, 区域及民族遗文化因素怎么和大模型做适配及finetune" 5 openai output/ai_podcast.wav minimax

# Use the included sample prompt file (8-minute show, default output path)
./generate_podcast.sh --topic-file sample_prompt.txt 8
```

Each MiniMax run prints a `🔐 Debug` line so you know the API key was detected (the value stays hidden—no secrets in the log).

That's it! The script will:
1. Generate a high-quality script using the LLM
2. Convert to speech using MiniMax's voices
3. Add natural silence between speakers
4. Output the final WAV file

## 📁 New Files Added

1. **`dataflow-ai-minimax.yml`** - Combined AI + MiniMax dataflow
2. **`nodes/dora-minimax-t2a/`** - MiniMax TTS node (copied from Dora repo)
3. **Updated `generate_podcast.sh`** - Now supports TTS backend selection
4. **Updated `.env.example`** - MiniMax configuration options
5. **Updated `README.md`** - Full documentation

## 🔧 Configuration Options

### Script Generation

```bash
# Choose LLM provider (default: openai)
LLM_PROVIDER=openai        # or anthropic

# Set script duration in minutes (default: 5)
SCRIPT_DURATION=10
```

### MiniMax TTS Tuning

Optional environment variables (defaults are already set in the dataflow):

```bash
# Voice speed: 0.5 (slow) to 2.0 (fast), default: 1.0
MINIMAX_SPEED=1.1

# Voice volume: 0.0 (silent) to 2.0 (loud), default: 1.0
MINIMAX_VOL=1.0

# Voice pitch: -12 (lower) to +12 (higher), default: 0
MINIMAX_PITCH=0

# Sample rate: 8000, 16000, 24000, or 32000 Hz, default: 32000
SAMPLE_RATE=32000

# Audio batching duration in milliseconds, default: 500
BATCH_DURATION_MS=2000
```

### Voice IDs

The dataflow uses these voice IDs by default:
- **大牛 (Daniu)**: `moss_audio_9c223de9-7ce1-11f0-9b9f-463feaa3106a` (speed: 1.1x)
- **一帆 (Yifan)**: `moss_audio_aaa1346a-7ce7-11f0-8e61-2e6e3c7ee85d` (speed: 1.0x)

To use different voices, edit `dataflow-ai-minimax.yml` and change the `MINIMAX_VOICE_ID` values.

## 📊 Comparison: Local vs Cloud

| Feature | PrimeSpeech (Local) | MiniMax (Cloud) |
|---------|-------------------|-----------------|
| **Setup Time** | ~30 min (model download) | < 1 min (API key only) |
| **Model Size** | ~10 GB | 0 GB (cloud-based) |
| **API Key Required** | No | Yes |
| **Cost** | Free (after download) | Pay-per-use |
| **Offline Support** | Yes | No (requires internet) |
| **Voice Quality** | High | Very High |
| **Voice Control** | Limited | Speed/pitch/volume |
| **Best For** | Offline use, high volume | Quick start, experimentation |

## 🔍 How It Works

### Architecture

```
User provides topic
    ↓
script-generator (LLM writes podcast script)
    ↓
script-segmenter (parses markdown, chunks text)
    ↓
    ├──→ minimax-daniu (TTS for 大牛 voice)
    └──→ minimax-yifan (TTS for 一帆 voice)
         ↓
voice-output (concatenates with silence)
    ↓
Final podcast.wav
```

### MiniMax WebSocket Flow

1. **Connect** to `wss://api.minimax.io/ws/v1/t2a_v2`
2. **Authenticate** with API key in headers
3. **Start task** with voice/audio settings
4. **Stream text** segment by segment
5. **Receive audio** as PCM chunks (16-bit)
6. **Batch chunks** to avoid memory issues
7. **Signal completion** after each segment

The node converts PCM int16 → float32 and sends to the voice-output node.

## 🛠️ Troubleshooting

### Error: MINIMAX_API_KEY not set

```bash
# Make sure you export the key
export MINIMAX_API_KEY=your-key-here

# Or add to .env file
echo "MINIMAX_API_KEY=your-key-here" >> .env
source .env
```

### Error: No audio output

Check MiniMax API quota and ensure your key is valid:
```bash
# Test MiniMax node directly
cd nodes/dora-minimax-t2a
export MINIMAX_API_KEY=your-key
python test_minimax_simple.py
```

### Error: Script generation failed

Verify LLM API key:
```bash
# For OpenAI
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# For Anthropic
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-3-5-sonnet-20241022","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'
```

### Slow synthesis

Try adjusting batch duration:
```bash
export BATCH_DURATION_MS=1000  # Larger batches (less frequent sends)
```

## 🎓 Advanced Usage

### Custom Dataflow

You can create your own dataflow by copying `dataflow-ai-minimax.yml` and modifying:

1. **Voice IDs**: Change to your custom MiniMax voices
2. **Speed/Pitch**: Adjust per-character voice characteristics
3. **Batch size**: Tune `BATCH_DURATION_MS` for your network
4. **LLM model**: Edit `script_generator_node.py` to use different models

### Manual Script with MiniMax

If you want to use MiniMax TTS with a pre-written script (no AI generation):

```bash
# Use dataflow-minimax.yml instead
cd /opt/airos/apps/podcast-generator

# Start dataflow
dora build dataflow-minimax.yml
dora start dataflow-minimax.yml --name podcast-generator --detach

# Run nodes
python voice_output.py --output-file output/manual_minimax.wav &
python script_segmenter.py --input-file scripts/your_script.md
```

### Programmatic Access

You can also use the components programmatically:

```python
from dora_minimax_t2a.config import MinimaxT2AConfig
from dora_minimax_t2a.minimax_client import MinimaxWebSocketClient
import asyncio

async def synthesize(text):
    config = MinimaxT2AConfig()
    client = MinimaxWebSocketClient(config)

    await client.connect()
    await client.start_task()

    audio_chunks = []
    async for sample_rate, audio_bytes in client.synthesize_streaming(text):
        audio_chunks.append(audio_bytes)

    await client.close()
    return audio_chunks

# Run
asyncio.run(synthesize("你好，世界"))
```

## 📚 Resources

- **MiniMax API Docs**: https://platform.minimax.io/document/T2A%E6%8E%A5%E5%8F%A3
- **OpenAI API**: https://platform.openai.com/docs
- **Anthropic API**: https://docs.anthropic.com/
- **Dora Framework**: https://dora-rs.ai

## 💡 Tips

1. **Start small**: Test with 2-3 minute podcasts first
2. **Monitor costs**: Both LLM and MiniMax charge per use
3. **Cache scripts**: Save generated scripts to reuse with different voices
4. **Use local for volume**: If generating many podcasts, download PrimeSpeech models
5. **Tune voices**: Experiment with speed/pitch to find your preferred style

## 🤝 Contributing

Found a bug or have a suggestion? Please open an issue in the main repository!

---

**Happy podcasting! 🎙️**
