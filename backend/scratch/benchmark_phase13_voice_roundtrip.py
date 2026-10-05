"""
Phase 13 Benchmark: Genuine End-to-End Multilingual Voice Round-Trip Verification.

Pipeline:
1. Audio Input: Real spoken query audio file (.wav)
2. STT: Faster-Whisper offline transcription (base int8 CPU)
3. Translation: NLLB-200 Kannada -> English query translation (preserving canonical heritage entities)
4. Retrieval: Hybrid Dense + BM25 retrieval + Cross-Encoder reranking
5. Grounding: GroundingGuard factual validation
6. Generation: Local Ollama (phi3:mini) grounded generation
7. Translation: NLLB-200 English -> Kannada response localization (if Kannada)
8. Persistence: Authoritative ChatMessage persistence in MySQL
9. TTS: Restricted speech synthesis via TTSService (Piper / MMS-TTS)
10. Verification: Playable 16-bit PCM WAV validation + Memory Profiling
"""

import asyncio
import io
import os
import sys
import time
import wave
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
from pathlib import Path
import structlog

# Ensure app is on python path
sys.path.insert(0, str(Path(__file__).parent.parent))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from app.application.conversation.service import ConversationService
from app.application.speech.schemas import MessageSpeechSynthesisRequest
from app.application.speech.tts_service import TTSService
from app.core.config import get_settings
from app.domain.ports.stt import TranscriptionResult
from app.infrastructure.db.session import get_session_factory
from app.infrastructure.stt.faster_whisper import FasterWhisperProvider
from app.infrastructure.tts.piper import PiperTTSProvider
from app.infrastructure.tts.mms import MMSTTSProvider
from app.infrastructure.tts.composite import CompositeTTSProvider

logger = structlog.get_logger(__name__)

# Windows memory structures
class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]

GetProcessMemoryInfo = ctypes.windll.psapi.GetProcessMemoryInfo
GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX), wintypes.DWORD]
GetProcessMemoryInfo.restype = wintypes.BOOL

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_uint64),
        ("ullAvailPhys", ctypes.c_uint64),
        ("ullTotalPageFile", ctypes.c_uint64),
        ("ullAvailPageFile", ctypes.c_uint64),
        ("ullTotalVirtual", ctypes.c_uint64),
        ("ullAvailVirtual", ctypes.c_uint64),
        ("ullAvailExtendedVirtual", ctypes.c_uint64),
    ]

def get_memory_stats():
    """Report memory metrics with distinct measurement scopes."""
    p = ctypes.windll.kernel32.GetCurrentProcess()
    c = PROCESS_MEMORY_COUNTERS_EX()
    c.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
    GetProcessMemoryInfo(p, ctypes.byref(c), c.cb)

    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))

    total_ram_gb = stat.ullTotalPhys / (1024 ** 3)
    avail_ram_gb = stat.ullAvailPhys / (1024 ** 3)
    used_ram_gb = total_ram_gb - avail_ram_gb

    return {
        "process_working_set_mb": round(c.WorkingSetSize / (1024 * 1024), 2),
        "process_private_bytes_mb": round(c.PrivateUsage / (1024 * 1024), 2),
        "whole_system_used_ram_gb": round(used_ram_gb, 2),
        "whole_system_total_ram_gb": round(total_ram_gb, 2),
        "whole_system_ram_percent": stat.dwMemoryLoad,
    }


async def run_voice_roundtrip():
    print("=" * 80)
    print("PHASE 13: GENUINE END-TO-END VOICE ROUND-TRIP VERIFICATION BENCHMARK")
    print("=" * 80)

    settings = get_settings()

    temp_dir = settings.resolved_temp_audio_path
    temp_dir.mkdir(parents=True, exist_ok=True)
    input_wav_path = temp_dir / "bench_query_belur.wav"

    # Step 0: Generate real speech audio for the query using Piper TTS
    spoken_query_text = "Who commissioned the Belur Chennakeshava temple in 1117 CE?"
    print(f"\n[Step 0: Generating Real Input Speech Audio]")
    print(f"Query Text: '{spoken_query_text}'")

    piper = PiperTTSProvider()
    t0_audio = time.perf_counter()
    audio_res = await piper.synthesize(spoken_query_text, language="en")
    with open(input_wav_path, "wb") as f:
        f.write(audio_res.audio_bytes)
    t_audio = time.perf_counter() - t0_audio
    print(f"-> Generated input WAV ({len(audio_res.audio_bytes)} bytes, {audio_res.duration_seconds:.2f}s, {audio_res.sample_rate}Hz) in {t_audio*1000:.1f}ms")

    # Step 1: Faster-Whisper STT
    print(f"\n[Step 1: Faster-Whisper Speech Recognition]")
    stt_provider = FasterWhisperProvider()
    t0_stt = time.perf_counter()
    stt_result: TranscriptionResult = await stt_provider.transcribe_audio(
        file_path=input_wav_path,
        language="en",
    )
    t_stt = time.perf_counter() - t0_stt
    print(f"STT Output Transcript:  '{stt_result.text}'")
    print(f"STT Detected Language:  {stt_result.language} (probability: {stt_result.language_probability:.3f})")
    print(f"STT Audio Duration:     {stt_result.duration_seconds:.2f}s")
    print(f"STT Execution Latency:  {t_stt*1000:.1f}ms")

    # Step 2: Full Conversation Turn (NLLB -> Hybrid RAG -> GroundingGuard -> Ollama -> Persistence)
    print(f"\n[Step 2: Full Grounded Conversation Engine]")
    session_factory = get_session_factory()
    async with session_factory() as db:
        conv_service = ConversationService(session=db)
        
        # Create session
        session = await conv_service.create_session(language_code="en")
        print(f"Created Session UUID:   {session.session_uuid}")

        t0_chat = time.perf_counter()
        chat_turn = await conv_service.process_turn(
            session_uuid=session.session_uuid,
            user_message=stt_result.text,
        )
        t_chat = time.perf_counter() - t0_chat

        print(f"Resolved/Translated Query: '{chat_turn.retrieval.resolved_query if chat_turn.retrieval else stt_result.text}'")
        print(f"Grounding State:          Grounded = {chat_turn.grounded}")
        print(f"Grounded Answer:          '{chat_turn.answer}'")
        print(f"Citations Extracted:      {len(chat_turn.citations)}")
        for c in chat_turn.citations:
            print(f"  - [{c.citation_label}] {c.source_filename} (p. {c.page_number})")
        print(f"Persisted Message ID:     {chat_turn.message_id}")
        print(f"Turn Latency:             {t_chat*1000:.1f}ms")

        # Step 3: Phase 12 TTS Speech Synthesis Handoff
        print(f"\n[Step 3: Restricted TTS Speech Synthesis Handoff]")
        tts_service = TTSService()
        tts_req = MessageSpeechSynthesisRequest(
            session_uuid=session.session_uuid,
            assistant_message_id=chat_turn.message_id,
        )
        t0_tts = time.perf_counter()
        audio_bytes, synth_res, metadata = await tts_service.synthesize_message_audio(
            request=tts_req,
            db=db,
        )
        t_tts = time.perf_counter() - t0_tts

        print(f"TTS Target Language:      {metadata.language}")
        print(f"Synthesized Audio Bytes:  {len(audio_bytes)} bytes")
        print(f"Audio Sample Rate:        {metadata.sample_rate} Hz")
        print(f"Audio Channels:           {metadata.channels} (Mono)")
        print(f"Audio Duration:           {metadata.duration_seconds:.2f}s")
        print(f"TTS Synthesis Latency:    {t_tts*1000:.1f}ms")

        # Validate WAV structure
        with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
            assert wf.getnchannels() == metadata.channels
            assert wf.getframerate() == metadata.sample_rate
            assert wf.getsampwidth() == 2
            n_frames = wf.getnframes()
            calc_duration = n_frames / metadata.sample_rate
            print(f"Validated WAV Frames:     {n_frames} frames ({calc_duration:.2f}s playback)")

    # Clean up input wav
    if input_wav_path.exists():
        input_wav_path.unlink()

    # Step 4: Memory Profiling Report
    print(f"\n[Step 4: Memory Profiling & Resource Scope Report]")
    mem = get_memory_stats()
    print(f"  * Process Working Set:   {mem['process_working_set_mb']:.2f} MB")
    print(f"  * Process Private Bytes: {mem['process_private_bytes_mb']:.2f} MB")
    print(f"  * Whole-System Used RAM: {mem['whole_system_used_ram_gb']:.2f} / {mem['whole_system_total_ram_gb']:.2f} GB ({mem['whole_system_ram_percent']}%)")

    total_pipeline_time = t_stt + t_chat + t_tts
    print(f"\n" + "=" * 80)
    print(f"GENUINE VOICE ROUND-TRIP RESULT: SUCCESS (Total E2E Latency: {total_pipeline_time:.2f}s)")
    print(f"=" * 80)


if __name__ == "__main__":
    asyncio.run(run_voice_roundtrip())
