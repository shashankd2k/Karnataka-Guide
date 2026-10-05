#!/usr/bin/env python3
"""
Deployment preflight model initialization and offline verification utility.
Used strictly during deployment verification to populate and validate persistent model caches.
Reuses existing production loaders and providers without duplicating model architecture.
"""

import argparse
import asyncio
import json
import os
import sys
import urllib.error
import urllib.request

# Ensure backend root is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if os.path.isdir(backend_dir):
    sys.path.insert(0, backend_dir)
else:
    # Running inside container where WORKDIR is /app and app/ is in /app/app
    sys.path.insert(0, os.path.abspath("."))

from app.core.config import get_settings


async def run_initialize() -> int:
    """
    Populate persistent cache volumes during online initialization.
    Reuses existing providers and loaders to download and cache required weights.
    """
    settings = get_settings()
    print("=" * 60)
    print("PHASE 17: ONLINE MODEL CACHE INITIALIZATION")
    print("=" * 60)
    errors = []

    # 1. Dense Embedding Model (all-MiniLM-L6-v2)
    print("\n[1/6] Initializing Dense Embeddings (SentenceTransformers)...")
    try:
        from app.application.knowledge.embeddings import get_embedding_model
        model = get_embedding_model(settings.EMBEDDING_MODEL)
        print(f"  -> SUCCESS: Loaded {settings.EMBEDDING_MODEL} ({type(model).__name__})")
    except Exception as e:
        print(f"  -> ERROR initializing Dense Embeddings: {e}")
        errors.append(("Dense Embeddings", str(e)))

    # 2. CrossEncoder Reranker (ms-marco-MiniLM-L-6-v2)
    print("\n[2/6] Initializing CrossEncoder Reranker...")
    try:
        from app.application.rag.reranker import get_cross_encoder_model
        ce_model = get_cross_encoder_model(settings.CROSS_ENCODER_MODEL)
        print(f"  -> SUCCESS: Loaded {settings.CROSS_ENCODER_MODEL} ({type(ce_model).__name__})")
    except Exception as e:
        print(f"  -> ERROR initializing CrossEncoder: {e}")
        errors.append(("CrossEncoder", str(e)))

    # 3. Faster-Whisper Base STT
    print("\n[3/6] Initializing Faster-Whisper Base STT...")
    try:
        from app.infrastructure.stt.faster_whisper import FasterWhisperProvider
        whisper_provider = FasterWhisperProvider(settings)
        whisper_ok = await whisper_provider.check_health()
        if whisper_ok:
            print(f"  -> SUCCESS: Faster-Whisper '{settings.WHISPER_MODEL}' cached and verified.")
        else:
            raise RuntimeError("FasterWhisperProvider.check_health() returned False")
    except Exception as e:
        print(f"  -> ERROR initializing Faster-Whisper: {e}")
        errors.append(("Faster-Whisper", str(e)))

    # 4. Meta NLLB-200 Translation Engine
    print("\n[4/6] Initializing Meta NLLB-200 Translation...")
    try:
        from app.infrastructure.translation.nllb import NLLBTranslationProvider
        nllb_provider = NLLBTranslationProvider()
        nllb_ok = await nllb_provider.check_health()
        if nllb_ok:
            print(f"  -> SUCCESS: NLLB-200 '{settings.TRANSLATION_MODEL_NAME}' cached and verified.")
        else:
            raise RuntimeError("NLLBTranslationProvider.check_health() returned False")
    except Exception as e:
        print(f"  -> ERROR initializing NLLB-200: {e}")
        errors.append(("NLLB-200", str(e)))

    # 5. Piper English TTS Voice Assets
    print("\n[5/6] Initializing Piper English TTS (Lessac Medium ONNX)...")
    try:
        from app.infrastructure.tts.piper import PiperTTSProvider
        piper_provider = PiperTTSProvider(auto_download=True)
        piper_ok = await piper_provider.check_health()
        if piper_ok:
            print("  -> SUCCESS: Piper English voice model cached and verified.")
        else:
            raise RuntimeError("PiperTTSProvider.check_health() returned False")
    except Exception as e:
        print(f"  -> ERROR initializing Piper TTS: {e}")
        errors.append(("Piper TTS", str(e)))

    # 6. Meta MMS-TTS Kannada Voice Engine
    print("\n[6/6] Initializing Meta MMS-TTS Kannada (VITS)...")
    try:
        from app.infrastructure.tts.mms import MMSTTSProvider
        mms_provider = MMSTTSProvider(local_files_only=False)
        mms_ok = await mms_provider.check_health()
        if mms_ok:
            print("  -> SUCCESS: MMS-TTS Kannada cached and verified.")
        else:
            raise RuntimeError("MMSTTSProvider.check_health() returned False")
    except Exception as e:
        print(f"  -> ERROR initializing MMS-TTS: {e}")
        errors.append(("MMS-TTS", str(e)))

    print("\n" + "=" * 60)
    if errors:
        print(f"ONLINE INITIALIZATION FAILED WITH {len(errors)} ERROR(S):")
        for name, err in errors:
            print(f"  - {name}: {err}")
        return 1
    else:
        print("ALL LOCAL MODEL CACHES POPULATED SUCCESSFULLY.")
        print("=" * 60)
        return 0


async def run_verify_offline() -> int:
    """
    Verify all required models load from persistent cache with zero WAN connectivity.
    Exits non-zero and identifies missing components if any model cannot load locally.
    """
    settings = get_settings()
    print("=" * 60)
    print("PHASE 17: OFFLINE MODEL CACHE VERIFICATION")
    print("=" * 60)
    errors = []

    # Enforce offline flags
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    # 1. Dense Embedding Model
    print("\n[1/7] Verifying Dense Embeddings (Offline)...")
    try:
        from sentence_transformers import SentenceTransformer
        # Strictly test local_files_only
        model = SentenceTransformer(settings.EMBEDDING_MODEL, local_files_only=True)
        print(f"  -> PASS: Dense embedding model '{settings.EMBEDDING_MODEL}' loaded offline.")
    except Exception as e:
        print(f"  -> FAIL: Dense embedding model missing or failed offline load: {e}")
        errors.append(("Dense Embeddings", str(e)))

    # 2. CrossEncoder Reranker
    print("\n[2/7] Verifying CrossEncoder Reranker (Offline)...")
    try:
        from sentence_transformers import CrossEncoder
        ce_model = CrossEncoder(settings.CROSS_ENCODER_MODEL, local_files_only=True)
        print(f"  -> PASS: CrossEncoder '{settings.CROSS_ENCODER_MODEL}' loaded offline.")
    except Exception as e:
        print(f"  -> FAIL: CrossEncoder missing or failed offline load: {e}")
        errors.append(("CrossEncoder", str(e)))

    # 3. Faster-Whisper Base STT
    print("\n[3/7] Verifying Faster-Whisper Base STT (Offline)...")
    try:
        from app.infrastructure.stt.faster_whisper import FasterWhisperProvider
        whisper_provider = FasterWhisperProvider(settings)
        whisper_ok = await whisper_provider.check_health()
        if whisper_ok:
            print(f"  -> PASS: Faster-Whisper '{settings.WHISPER_MODEL}' verified offline.")
        else:
            raise RuntimeError("FasterWhisperProvider.check_health() returned False")
    except Exception as e:
        print(f"  -> FAIL: Faster-Whisper offline verification failed: {e}")
        errors.append(("Faster-Whisper", str(e)))

    # 4. Meta NLLB-200 Translation Engine
    print("\n[4/7] Verifying Meta NLLB-200 Translation (Offline)...")
    try:
        from app.infrastructure.translation.nllb import NLLBTranslationProvider
        nllb_provider = NLLBTranslationProvider()
        nllb_ok = await nllb_provider.check_health()
        if nllb_ok:
            print(f"  -> PASS: NLLB-200 '{settings.TRANSLATION_MODEL_NAME}' verified offline.")
        else:
            raise RuntimeError("NLLBTranslationProvider.check_health() returned False")
    except Exception as e:
        print(f"  -> FAIL: NLLB-200 offline verification failed: {e}")
        errors.append(("NLLB-200", str(e)))

    # 5. Piper English TTS Voice Assets
    print("\n[5/7] Verifying Piper English TTS (Offline)...")
    try:
        from app.infrastructure.tts.piper import PiperTTSProvider
        piper_provider = PiperTTSProvider(auto_download=False)
        piper_ok = await piper_provider.check_health()
        if piper_ok:
            print("  -> PASS: Piper English voice model verified offline.")
        else:
            raise RuntimeError("PiperTTSProvider.check_health() returned False")
    except Exception as e:
        print(f"  -> FAIL: Piper TTS voice assets missing offline: {e}")
        errors.append(("Piper TTS", str(e)))

    # 6. Meta MMS-TTS Kannada Voice Engine
    print("\n[6/7] Verifying Meta MMS-TTS Kannada (Offline)...")
    try:
        from app.infrastructure.tts.mms import MMSTTSProvider
        mms_provider = MMSTTSProvider(local_files_only=True)
        mms_ok = await mms_provider.check_health()
        if mms_ok:
            print("  -> PASS: MMS-TTS Kannada verified offline.")
        else:
            raise RuntimeError("MMSTTSProvider.check_health() returned False")
    except Exception as e:
        print(f"  -> FAIL: MMS-TTS Kannada missing offline: {e}")
        errors.append(("MMS-TTS", str(e)))

    # 7. Ollama Local LLM Presence
    print("\n[7/7] Verifying Ollama Local LLM (phi3:mini)...")
    try:
        url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("name") for m in data.get("models", [])]
                matched = any(settings.OLLAMA_MODEL in m for m in models)
                if matched:
                    print(f"  -> PASS: Ollama reports model '{settings.OLLAMA_MODEL}' present locally: {models}")
                else:
                    raise RuntimeError(
                        f"Model '{settings.OLLAMA_MODEL}' not found in Ollama models list: {models}"
                    )
            else:
                raise RuntimeError(f"Ollama returned HTTP {resp.status}")
    except Exception as e:
        print(f"  -> FAIL: Ollama verification failed: {e}")
        errors.append(("Ollama phi3:mini", str(e)))

    print("\n" + "=" * 60)
    if errors:
        print(f"OFFLINE VERIFICATION FAILED WITH {len(errors)} MISSING COMPONENT(S):")
        for name, err in errors:
            print(f"  - {name}: {err}")
        return 1
    else:
        print("ALL REQUIRED MODELS VERIFIED PRESENT AND LOADABLE OFFLINE.")
        print("=" * 60)
        return 0


def main():
    parser = argparse.ArgumentParser(description="Phase 17 Model Preflight Utility")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--initialize",
        action="store_true",
        help="Populate persistent cache volumes during initial online setup",
    )
    group.add_argument(
        "--verify-offline",
        action="store_true",
        help="Verify all required models load locally without WAN access",
    )

    args = parser.parse_args()
    if args.initialize:
        sys.exit(asyncio.run(run_initialize()))
    elif args.verify_offline:
        sys.exit(asyncio.run(run_verify_offline()))


if __name__ == "__main__":
    main()
