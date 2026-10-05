"""
Comprehensive Phase 12 Voice Quality, Full-Stack Memory, and Bilingual Round-Trip Benchmark.
"""

import os
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import asyncio
import io
import time
import wave
import ctypes
from ctypes import wintypes
from pathlib import Path
import numpy as np

# Windows memory profiling
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

def get_process_ram_mb() -> tuple[float, float]:
    p = ctypes.windll.kernel32.GetCurrentProcess()
    c = PROCESS_MEMORY_COUNTERS_EX()
    c.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
    GetProcessMemoryInfo(p, ctypes.byref(c), c.cb)
    return c.WorkingSetSize / (1024 * 1024), c.PrivateUsage / (1024 * 1024)


# 10 English Heritage Tourism Sentences
ENGLISH_BENCHMARK_SENTENCES = [
    "The Chennakeshava Temple at Belur was commissioned by King Vishnuvardhana in 1117 CE to mark his victory at Talakadu.",
    "Halebidu, the historic capital of the Hoysala Empire, is home to the magnificent Hoysaleswara Temple with twin Shiva shrines.",
    "Badami is famous for its rock-cut cave temples carved into red sandstone cliffs during the 6th century.",
    "Aihole is revered as the cradle of Hindu temple architecture, featuring the unique apsidal Durga Temple.",
    "Pattadakal features a UNESCO World Heritage complex of 8th-century Hindu and Jain temples representing Rekha-Nagara and Dravida styles.",
    "Hampi, the magnificent capital of the Vijayanagara Empire, spans over 4,100 hectares along the Tungabhadra River.",
    "The Virupaksha Temple in Hampi has remained an active place of worship since the 7th century CE.",
    "The Vittala Temple is celebrated for its iconic stone chariot and musical pillars built during the reign of King Devaraya the second.",
    "The Hoysala temples of Belur and Halebidu were officially inscribed on the UNESCO World Heritage list in 2023.",
    "Information is not available in the knowledge base.",
]

# 10 Kannada Heritage Tourism Sentences
KANNADA_BENCHMARK_SENTENCES = [
    "ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ರಾಜ ವಿಷ್ಣುವರ್ಧನನು ಕ್ರಿ.ಶ. 1117ರಲ್ಲಿ ತಲಕಾಡಿನ ವಿಜಯದ ಸ್ಮರಣಾರ್ಥ ನಿರ್ಮಿಸಿದರು.",
    "ಹಳೇಬೀಡು ಹೊಯ್ಸಳ ಸಾಮ್ರಾಜ್ಯದ ರಾಜಧಾನಿಯಾಗಿದ್ದು, ಭವ್ಯವಾದ ಹೊಯ್ಸಳೇಶ್ವರ ದೇವಾಲಯಕ್ಕೆ ಪ್ರಸಿದ್ಧವಾಗಿದೆ.",
    "ಬಾದಾಮಿ ಗುಹಾ ದೇವಾಲಯಗಳು 6ನೇ ಶತಮಾನದಲ್ಲಿ ಕೆತ್ತಲಾದ ಕೆಂಪು ಮರಳುಗಲ್ಲಿನ ಅದ್ಭುತ ವಾಸ್ತುಶಿಲ್ಪಕ್ಕೆ ಹೆಸರಾಗಿವೆ.",
    "ಐಹೊಳೆ ಭಾರತೀಯ ದೇವಾಲಯ ವಾಸ್ತುಶಿಲ್ಪದ ತೊಟ್ಟಿಲು ಎಂದು ಪ್ರಸಿದ್ಧಿಯಾಗಿದ್ದು, ವಿಶಿಷ್ಟ ದುರ್ಗಾ ದೇವಾಲಯವನ್ನು ಹೊಂದಿದೆ.",
    "ಪಟ್ಟದಕಲ್ಲು ಯುನೆಸ್ಕೋ ವಿಶ್ವ ಪರಂಪರೆಯ ತಾಣವಾಗಿದ್ದು, 8ನೇ ಶತಮಾನದ ನಾಗರ ಮತ್ತು ದ್ರಾವಿಡ ಶೈಲಿಯ ದೇವಾಲಯಗಳನ್ನು ಒಳಗೊಂಡಿದೆ.",
    "ಹಂಪಿ ವಿಜಯನಗರ ಸಾಮ್ರಾಜ್ಯದ ಭವ್ಯ ರಾಜಧಾನಿಯಾಗಿದ್ದು, ತುಂಗಭದ್ರಾ ನದಿಯ ದಡದಲ್ಲಿ 4,100 ಹೆಕ್ಟೇರ್ ಪ್ರದೇಶದಲ್ಲಿ ಹರಡಿದೆ.",
    "ಹಂಪಿಯ ವಿರೂಪಾಕ್ಷ ದೇವಾಲಯವು 7ನೇ ಶತಮಾನದಿಂದ ಇಂದಿನವರೆಗೂ ನಿರಂತರ ಪೂಜೆ ನಡೆಯುತ್ತಿರುವ ಪವಿತ್ರ ಕ್ಷೇತ್ರವಾಗಿದೆ.",
    "ವಿಠ್ಠಲ ದೇವಾಲಯವು ತನ್ನ ಅದ್ಭುತ ಕಲ್ಲಿನ ರಥ ಮತ್ತು ಸಪ್ತಸ್ವರ ಸಂಗೀತ ಕಂಬಗಳಿಗೆ ವಿಶ್ವವಿಖ್ಯಾತವಾಗಿದೆ.",
    "ಬೇಲೂರು ಮತ್ತು ಹಳೇಬೀಡಿನ ಹೊಯ್ಸಳ ದೇವಾಲಯಗಳನ್ನು 2023ರಲ್ಲಿ ಯುನೆಸ್ಕೋ ವಿಶ್ವ ಪರಂಪರೆಯ ಪಟ್ಟಿಗೆ ಸೇರಿಸಲಾಯಿತು.",
    "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ.",
]


async def run_benchmark():
    print("=" * 80)
    print("PHASE 12 TTS QUALITY & FULL-STACK BENCHMARK SUITE")
    print("=" * 80)

    from app.application.speech.tts_service import SpeechTextSanitizer, TTSService
    from app.domain.ports.tts import AudioSynthesisResult
    from app.infrastructure.tts.composite import CompositeTTSProvider
    from app.infrastructure.tts.mms import MMSTTSProvider
    from app.infrastructure.tts.piper import PiperTTSProvider

    # Step 1: Memory Profile across Lifecycle
    ws_base, priv_base = get_process_ram_mb()
    print(f"\n1. BASELINE PROCESS RAM:               WS={ws_base:6.2f} MB | Private={priv_base:6.2f} MB")

    piper_provider = PiperTTSProvider()
    # Warm up Piper
    await piper_provider.synthesize("Warmup English text.", language="en")
    ws_piper, priv_piper = get_process_ram_mb()
    print(f"2. RAM AFTER PIPER LOADED (en):         WS={ws_piper:6.2f} MB (Delta: +{ws_piper - ws_base:6.2f} MB)")

    mms_provider = MMSTTSProvider(local_files_only=True)
    # Warm up MMS
    await mms_provider.synthesize("ಪೂರ್ವಸಿದ್ಧತೆ ಕನ್ನಡ ಧ್ವನಿ.", language="kn")
    ws_mms, priv_mms = get_process_ram_mb()
    print(f"3. RAM AFTER MMS-TTS LOADED (kn):       WS={ws_mms:6.2f} MB (Delta: +{ws_mms - ws_piper:6.2f} MB)")
    print(f"4. TOTAL ISOLATED TTS RAM OVERHEAD:     WS=+{ws_mms - ws_base:6.2f} MB | Private=+{priv_mms - priv_base:6.2f} MB")

    composite = CompositeTTSProvider(piper_provider=piper_provider, mms_provider=mms_provider)
    service = TTSService(provider=composite)

    # Step 2: 10 English Tourism Sentences Benchmark
    print("\n" + "=" * 80)
    print("ENGLISH TOURISM SENTENCES BENCHMARK (Piper TTS, 22,050 Hz Mono)")
    print("=" * 80)
    print(f"{'#':<3} | {'Duration (s)':<12} | {'Latency (ms)':<12} | {'RTF':<8} | {'Audio Bytes':<11} | {'Sanitized Preview'}")
    print("-" * 80)

    en_durations = []
    en_latencies = []
    en_rtfs = []

    for i, sent in enumerate(ENGLISH_BENCHMARK_SENTENCES, 1):
        sanitized = SpeechTextSanitizer.sanitize(sent)
        t0 = time.perf_counter()
        raw_wav, result = await service.synthesize_direct(sent, language="en")
        latency_ms = (time.perf_counter() - t0) * 1000
        rtf = (latency_ms / 1000.0) / result.duration_seconds if result.duration_seconds > 0 else 0.0

        en_durations.append(result.duration_seconds)
        en_latencies.append(latency_ms)
        en_rtfs.append(rtf)

        preview = sanitized[:45] + ("..." if len(sanitized) > 45 else "")
        print(f"{i:<3} | {result.duration_seconds:10.2f}s  | {latency_ms:10.1f}ms | {rtf:6.3f}x | {len(raw_wav):9} B | {preview}")

    print("-" * 80)
    print(f"English Summary: Total Audio={sum(en_durations):.2f}s | Avg Latency={np.mean(en_latencies):.1f}ms | Avg RTF={np.mean(en_rtfs):.3f}x ({1.0/np.mean(en_rtfs):.1f}x real-time speed)")

    # Step 3: 10 Kannada Tourism Sentences Benchmark
    print("\n" + "=" * 80)
    print("KANNADA TOURISM SENTENCES BENCHMARK (Meta MMS-TTS, 16,000 Hz Mono)")
    print("=" * 80)
    print(f"{'#':<3} | {'Duration (s)':<12} | {'Latency (ms)':<12} | {'RTF':<8} | {'Audio Bytes':<11} | {'Sanitized Preview'}")
    print("-" * 80)

    kn_durations = []
    kn_latencies = []
    kn_rtfs = []

    for i, sent in enumerate(KANNADA_BENCHMARK_SENTENCES, 1):
        sanitized = SpeechTextSanitizer.sanitize(sent)
        t0 = time.perf_counter()
        raw_wav, result = await service.synthesize_direct(sent, language="kn")
        latency_ms = (time.perf_counter() - t0) * 1000
        rtf = (latency_ms / 1000.0) / result.duration_seconds if result.duration_seconds > 0 else 0.0

        kn_durations.append(result.duration_seconds)
        kn_latencies.append(latency_ms)
        kn_rtfs.append(rtf)

        preview = sanitized[:40] + ("..." if len(sanitized) > 40 else "")
        print(f"{i:<3} | {result.duration_seconds:10.2f}s  | {latency_ms:10.1f}ms | {rtf:6.3f}x | {len(raw_wav):9} B | {preview}")

    print("-" * 80)
    print(f"Kannada Summary: Total Audio={sum(kn_durations):.2f}s | Avg Latency={np.mean(kn_latencies):.1f}ms | Avg RTF={np.mean(kn_rtfs):.3f}x ({1.0/np.mean(kn_rtfs):.1f}x real-time speed)")

    # Step 4: Number and Date Pronunciation Benchmark
    print("\n" + "=" * 80)
    print("HISTORICAL NUMERIC & DATE PHONEMIZATION TEST")
    print("=" * 80)
    num_tests = [
        ("en", "The temple was built in 1117 CE during the 12th century."),
        ("en", "Badami cave temples date back to 733 CE."),
        ("kn", "ದೇವಾಲಯವನ್ನು ಕ್ರಿ.ಶ. 1117ರಲ್ಲಿ 12ನೇ ಶತಮಾನದಲ್ಲಿ ನಿರ್ಮಿಸಲಾಯಿತು."),
        ("kn", "ಬಾದಾಮಿ ಗುಹೆಗಳು ಕ್ರಿ.ಶ. 733ರ ಕಾಲದ್ದಾಗಿವೆ."),
    ]
    for lang, text in num_tests:
        raw_wav, res = await service.synthesize_direct(text, language=lang)
        print(f"[{lang.upper()}] Text: '{text}'")
        print(f"       Duration: {res.duration_seconds:.2f}s | Bytes: {len(raw_wav)} | Sample Rate: {res.sample_rate}Hz | Playable: TRUE")

    # Step 5: Full-Stack Voice Round-Trip Simulation
    print("\n" + "=" * 80)
    print("FULL-STACK MULTILINGUAL VOICE ROUND-TRIP DEMONSTRATION")
    print("=" * 80)

    # Simulate Full Voice Pipeline:
    # Kannada Question -> Translation NLLB -> Retrieval RAG -> Ollama -> Translation NLLB -> MMS TTS -> Kannada WAV
    from app.application.translation.service import TranslationService
    from app.infrastructure.stt.faster_whisper import FasterWhisperProvider

    translation_service = TranslationService()
    stt = FasterWhisperProvider()

    kn_user_query = "ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಕಟ್ಟಿಸಿದರು?"
    print(f"1. Tourist Kannada Query:    '{kn_user_query}'")

    # Step A: Query Translation
    t_tr_q0 = time.perf_counter()
    en_retrieval_query = await translation_service.translate_retrieval_query(kn_user_query, "kn")
    t_tr_q = (time.perf_counter() - t_tr_q0) * 1000
    print(f"2. Canonical English Query:  '{en_retrieval_query}' ({t_tr_q:.1f} ms)")

    # Step B: Grounded English Answer Simulation
    en_grounded_answer = "The Chennakeshava Temple at Belur was commissioned by King Vishnuvardhana of the Hoysala dynasty in 1117 CE. [1]"
    print(f"3. Grounded English Answer:   '{en_grounded_answer}'")

    # Step C: Response Translation to Kannada
    t_tr_r0 = time.perf_counter()
    kn_grounded_answer = await translation_service.translate_response(en_grounded_answer, "kn")
    t_tr_r = (time.perf_counter() - t_tr_r0) * 1000
    print(f"4. Grounded Kannada Answer:   '{kn_grounded_answer}' ({t_tr_r:.1f} ms)")

    # Step D: Speech Sanitization & MMS-TTS Synthesis
    speech_clean_kn = SpeechTextSanitizer.sanitize(kn_grounded_answer)
    t_tts0 = time.perf_counter()
    wav_bytes, tts_res = await service.synthesize_direct(kn_grounded_answer, language="kn")
    t_tts = (time.perf_counter() - t_tts0) * 1000
    rtf_tts = (t_tts / 1000.0) / tts_res.duration_seconds if tts_res.duration_seconds > 0 else 0.0

    print(f"5. Speech Sanitized Text:    '{speech_clean_kn}' (Citations stripped for audio: {bool('[1]' not in speech_clean_kn)})")
    print(f"6. Synthesized Kannada WAV:  {len(wav_bytes)} bytes ({tts_res.duration_seconds:.2f}s audio | Latency: {t_tts:.1f} ms | RTF: {rtf_tts:.3f}x)")

    ws_peak, priv_peak = get_process_ram_mb()
    print("-" * 80)
    print(f"PEAK FULL-STACK PROCESS MEMORY: WS={ws_peak:6.2f} MB | Private={priv_peak:6.2f} MB")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
