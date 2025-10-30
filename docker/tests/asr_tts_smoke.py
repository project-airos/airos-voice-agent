#!/usr/bin/env python3
"""Lightweight smoke tests for ASR and TTS stacks.

These tests run inside the airos-voice-agent Docker image and validate that
core components boot, load their models, and complete a minimal inference.
The script intentionally keeps external dependencies to a minimum so it can
run as part of CI or manual smoke checks before starting the full dataflow.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np


def _print_json(prefix: str, payload: dict) -> None:
    """Pretty-print a JSON payload with a prefix."""
    formatted = json.dumps(payload, indent=2, ensure_ascii=False)
    print(f"\n{prefix}:\n{formatted}")


def run_asr(sample_seconds: float = 2.0) -> bool:
    """Run a basic ASR transcription using the configured engine."""
    from dora_asr.config import ASRConfig
    from dora_asr.manager import ASRManager

    config = ASRConfig()
    manager = ASRManager()

    sample_rate = config.SAMPLE_RATE or 16_000
    total_samples = max(int(sample_rate * sample_seconds), sample_rate)

    # Generate a simple 220 Hz sine tone with gentle fade in/out.
    time_axis = np.arange(total_samples, dtype=np.float32) / sample_rate
    audio = np.sin(2 * np.pi * 220 * time_axis).astype(np.float32) * 0.05

    # Apply a Hann window to avoid sharp edges that could break the FFT front-end.
    if len(audio) > 1024:
        window = np.hanning(len(audio)).astype(np.float32)
        audio *= window

    print("Running ASR smoke test…")
    print(f"  Engine: {config.ASR_ENGINE}")
    print(f"  Sample rate: {sample_rate} Hz")
    print(f"  Duration: {sample_seconds:.2f} s")

    result = manager.transcribe(audio, language=config.LANGUAGE)
    _print_json(
        "ASR result",
        {
            "language": result.get("language"),
            "text_preview": (result.get("text", "") or "").strip()[:120],
            "segments": result.get("segments")[:1] if result.get("segments") else None,
        },
    )

    manager.cleanup()
    return True


def run_tts(output_dir: Optional[Path] = None) -> bool:
    """Run a basic TTS synthesis using PrimeSpeech."""
    from dora_primespeech.config import PrimeSpeechConfig, VOICE_CONFIGS
    from dora_primespeech.model_manager import ModelManager
    from dora_primespeech.moyoyo_tts_wrapper_streaming_fix import (
        StreamingMoYoYoTTSWrapper,
        MOYOYO_AVAILABLE,
    )

    # Disable G2PW for smoke test to avoid dependency on optional model
    os.environ["AIROS_ENABLE_G2PW"] = "False"

    config = PrimeSpeechConfig()
    voice_name = config.VOICE_NAME if config.VOICE_NAME in VOICE_CONFIGS else "Doubao"
    voice_config = VOICE_CONFIGS[voice_name].copy()

    models_dir = config.get_models_dir()
    os.environ.setdefault("PRIMESPEECH_MODEL_DIR", str(models_dir))

    manager = ModelManager(models_dir)
    manager.get_voice_model_paths(voice_name, voice_config)

    if not MOYOYO_AVAILABLE:
        print("⚠️  MoYoYo TTS Python package is not available. Skipping TTS smoke test.")
        return False

    print("Running TTS smoke test…")
    print(f"  Voice: {voice_name}")
    print(f"  Models directory: {models_dir}")

    wrapper = StreamingMoYoYoTTSWrapper(
        voice=voice_name,
        device=config.DEVICE,
        enable_streaming=False,
        voice_config=voice_config,
        logger_func=lambda level, message: print(f"[{level}] {message}"),
    )

    text = "你好，这是 AIROS PrimeSpeech 的语音合成测试。我们正在验证容器内的 TTS 依赖是否就绪。"
    sample_rate, audio = wrapper.synthesize(
        text,
        language=voice_config.get("text_lang", config.TEXT_LANG or "auto"),
        speed=voice_config.get("speed_factor", config.SPEED_FACTOR),
    )

    if output_dir is None:
        output_dir = Path(tempfile.gettempdir())
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "primespeech-smoke.wav"

    from soundfile import write as sf_write

    sf_write(output_path, audio, sample_rate)

    _print_json(
        "TTS result",
        {
            "sample_rate": sample_rate,
            "duration_sec": round(len(audio) / sample_rate, 3),
            "output_path": str(output_path),
        },
    )

    return True


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="ASR/TTS smoke test runner")
    parser.add_argument(
        "--asr",
        action="store_true",
        help="Run the ASR smoke test",
    )
    parser.add_argument(
        "--tts",
        action="store_true",
        help="Run the TTS smoke test",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional directory for synthesized audio output",
    )

    args = parser.parse_args(argv)

    # If neither flag provided, run both.
    run_asr_test = args.asr or (not args.asr and not args.tts)
    run_tts_test = args.tts or (not args.asr and not args.tts)

    success = True

    if run_asr_test:
        try:
            success &= run_asr()
        except Exception as exc:  # pragma: no cover - smoke test error path
            print(f"❌ ASR smoke test failed: {exc}", file=sys.stderr)
            return 1

    if run_tts_test:
        try:
            success &= run_tts(args.output_dir)
        except Exception as exc:  # pragma: no cover - smoke test error path
            print(f"❌ TTS smoke test failed: {exc}", file=sys.stderr)
            return 1

    if success:
        print("\n✅ Smoke tests completed")
    else:
        print("\n⚠️  Smoke tests completed with warnings")

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
