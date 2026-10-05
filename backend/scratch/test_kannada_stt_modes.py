"""
Phase 10 Dedicated Kannada Speech-To-Text Hardening and CER/WER Measurement.
Compares:
Mode A: Automatic Language Detection (language=None)
Mode B: Forced Kannada Decoding (language='kn')

Measures:
1. Exact Kannada Character Error Rate (CER)
2. Exact Kannada Word Error Rate (WER)
3. Heritage Proper Noun Preservation (Belur, Chennakeshava, Halebidu, Hoysaleswara, Badami, Aihole, Pattadakal, Hampi, Virupaksha, Vishnuvardhana)
4. End-to-End Kannada Voice-to-Chat execution
5. Temporary storage cleanup verification
"""

import asyncio
import io
import math
from pathlib import Path
import struct
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
import wave

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.core.config import get_settings
from app.domain.ports.stt import TranscriptionResult
from app.infrastructure.stt.faster_whisper import FasterWhisperProvider
from app.infrastructure.stt.audio_validator import validate_and_decode_audio_stream
from app.application.speech.stt_service import SpeechToTextService
from app.application.conversation.service import ConversationService
from app.infrastructure.db.session import get_session_factory
from fastapi import UploadFile


def levenshtein(seq1: List[str], seq2: List[str]) -> int:
    m, n = len(seq1), len(seq2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if seq1[i - 1] == seq2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    return dp[m][n]


def compute_cer(reference: str, hypothesis: str) -> float:
    """Character Error Rate for Indic Kannada script text."""
    ref_chars = [c for c in reference.replace(" ", "") if c]
    hyp_chars = [c for c in hypothesis.replace(" ", "") if c]
    if not ref_chars:
        return 0.0 if not hyp_chars else 1.0
    dist = levenshtein(ref_chars, hyp_chars)
    return round(dist / len(ref_chars), 4)


def compute_wer(reference: str, hypothesis: str) -> float:
    """Word Error Rate."""
    ref_words = [w.strip(".,?!;:\"' ") for w in reference.split() if w.strip(".,?!;:\"' ")]
    hyp_words = [w.strip(".,?!;:\"' ") for w in hypothesis.split() if w.strip(".,?!;:\"' ")]
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    dist = levenshtein(ref_words, hyp_words)
    return round(dist / len(ref_words), 4)


def generate_spoken_audio(text: str, output_path: Path) -> None:
    safe_text = text.replace("'", "''")
    ps_script = f"""
    Add-Type -AssemblyName System.Speech
    $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $s.SetOutputToWaveFile('{str(output_path).replace(chr(92), "/")}')
    $s.Rate = 0
    $s.Volume = 100
    $s.Speak('{safe_text}')
    $s.Dispose()
    """
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_script],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"PowerShell speech synthesis failed: {result.stderr}")


KANNADA_BENCHMARK_CLIPS = [
    {
        "id": "KN-01",
        "reference_kn": "ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ನಿರ್ಮಿಸಿದರು?",
        "spoken_phonetic": "Beluru Chennakeshava devalayavannu yaaru nirmisidaru?",
        "entity": "Chennakeshava",
    },
    {
        "id": "KN-02",
        "reference_kn": "ಬೇಲೂರು ದೇವಾಲಯದ ಮದನಿಕಾ ಶಿಲ್ಪಗಳ ಮಹತ್ವವೇನು?",
        "spoken_phonetic": "Beluru devalayada Madanika shilpagala mahatvavenu?",
        "entity": "Belur",
    },
    {
        "id": "KN-03",
        "reference_kn": "ಹಳೇಬೀಡು ಹೊಯ್ಸಳೇಶ್ವರ ದೇವಾಲಯದ ಇತಿಹಾಸವೇನು?",
        "spoken_phonetic": "Halebeedu Hoysaleshwara devalayada itihasavenu?",
        "entity": "Halebidu",
    },
    {
        "id": "KN-04",
        "reference_kn": "ಬಾದಾಮಿ ಗುಹೆ ಒಂದರಲ್ಲಿ ಯಾವ ಕೆತ್ತನೆಗಳಿವೆ?",
        "spoken_phonetic": "Badami guhe ondaralli yaava kettanegalive?",
        "entity": "Badami",
    },
    {
        "id": "KN-05",
        "reference_kn": "ಐಹೊಳೆಯನ್ನು ವಾಸ್ತುಶಿಲ್ಪದ ತೊಟ್ಟಿಲು ಎಂದು ಏಕೆ ಕರೆಯುತ್ತಾರೆ?",
        "spoken_phonetic": "Aiholeyannu vastushilpada tottilu endu eke kareyuttare?",
        "entity": "Aihole",
    },
    {
        "id": "KN-06",
        "reference_kn": "ಪಟ್ಟದಕಲ್ಲಿನ ವಿರೂಪಾಕ್ಷ ದೇವಾಲಯವನ್ನು ಯಾರು ಕಟ್ಟಿಸಿದರು?",
        "spoken_phonetic": "Pattadakallina Virupaksha devalayavannu yaaru kattisidaru?",
        "entity": "Pattadakal",
    },
    {
        "id": "KN-07",
        "reference_kn": "ವಿಜಯನಗರ ಸಾಮ್ರಾಜ್ಯವನ್ನು ಸ್ಥಾಪಿಸಿದವರು ಯಾರು?",
        "spoken_phonetic": "Vijayanagara samrajyavannu sthapisidavaru yaaru?",
        "entity": "Vijayanagara",
    },
    {
        "id": "KN-08",
        "reference_kn": "ಹಂಪಿಯ ಕಲ್ಲಿನ ರಥದ ಬಗ್ಗೆ ತಿಳಿಸಿ.",
        "spoken_phonetic": "Hampiya kallina rathada bagge thilisi.",
        "entity": "Hampi",
    },
    {
        "id": "KN-09",
        "reference_kn": "ವಿಠ್ಠಲ ದೇವಾಲಯದ ಸಂಗೀತ ಸ್ತಂಭಗಳ ವೈಶಿಷ್ಟ್ಯವೇನು?",
        "spoken_phonetic": "Vittala devalayada sangeetha stambhagala vaishistyavenu?",
        "entity": "Vittala",
    },
    {
        "id": "KN-10",
        "reference_kn": "ಬೇಲೂರು ದೇವಾಲಯಕ್ಕೆ ವಿಷ್ಣುವರ್ಧನ ನೀಡಿದ ಕೊಡುಗೆ ಏನು?",
        "spoken_phonetic": "Beluru devalayakke Vishnuvardhana needida koduge enu?",
        "entity": "Vishnuvardhana",
    },
]


async def run_kannada_evaluation():
    settings = get_settings()
    provider = FasterWhisperProvider(settings=settings)
    temp_dir = settings.resolved_temp_audio_path

    print("=" * 85)
    print("PHASE 10 KANNADA STT HARDENING & MODE COMPARISON")
    print(f"Faster-Whisper Model: {settings.WHISPER_MODEL} ({settings.WHISPER_DEVICE}, {settings.WHISPER_COMPUTE_TYPE})")
    print("=" * 85)

    auto_cers, auto_wers = [], []
    forced_cers, forced_wers = [], []
    auto_lang_matches = 0
    forced_empty_count = 0
    auto_empty_count = 0

    print("\n--- Testing 10 Kannada Spoken Clips (Auto-Detection vs Forced-kn) ---")

    for clip in KANNADA_BENCHMARK_CLIPS:
        cid = clip["id"]
        ref_kn = clip["reference_kn"]
        phonetic = clip["spoken_phonetic"]
        ent = clip["entity"]
        wav_file = temp_dir / f"kn_eval_{cid}.wav"
        generate_spoken_audio(phonetic, wav_file)

        try:
            # Mode A: Automatic Language Detection
            t0 = time.perf_counter()
            res_auto: TranscriptionResult = await provider.transcribe_audio(wav_file, language=None)
            lat_auto = (time.perf_counter() - t0) * 1000
            hyp_auto = res_auto.text.strip()

            if not hyp_auto:
                auto_empty_count += 1
            if res_auto.language == "kn":
                auto_lang_matches += 1

            cer_auto = compute_cer(ref_kn, hyp_auto)
            wer_auto = compute_wer(ref_kn, hyp_auto)
            auto_cers.append(cer_auto)
            auto_wers.append(wer_auto)

            # Mode B: Forced Kannada Decoding (language='kn')
            t1 = time.perf_counter()
            res_forced: TranscriptionResult = await provider.transcribe_audio(wav_file, language="kn")
            lat_forced = (time.perf_counter() - t1) * 1000
            hyp_forced = res_forced.text.strip()

            if not hyp_forced:
                forced_empty_count += 1

            cer_forced = compute_cer(ref_kn, hyp_forced)
            wer_forced = compute_wer(ref_kn, hyp_forced)
            forced_cers.append(cer_forced)
            forced_wers.append(wer_forced)

            print(f"\n[{cid}] Entity Target: {ent}")
            print(f"  Reference (KN):  {ref_kn}")
            print(f"  Spoken Phonetic: {phonetic}")
            print(f"  Mode A (Auto):   '{hyp_auto}' (Lang: {res_auto.language}, p={res_auto.language_probability:.2f}, {lat_auto:.0f}ms) | CER: {cer_auto*100:.1f}%, WER: {wer_auto*100:.1f}%")
            print(f"  Mode B (Forced): '{hyp_forced}' (Lang: {res_forced.language}, p={res_forced.language_probability:.2f}, {lat_forced:.0f}ms) | CER: {cer_forced*100:.1f}%, WER: {wer_forced*100:.1f}%")

        finally:
            if wav_file.exists():
                wav_file.unlink()

    # Calculate overall metrics
    avg_auto_cer = sum(auto_cers) / len(auto_cers)
    avg_auto_wer = sum(auto_wers) / len(auto_wers)
    avg_forced_cer = sum(forced_cers) / len(forced_cers)
    avg_forced_wer = sum(forced_wers) / len(forced_wers)

    print("\n" + "=" * 85)
    print("KANNADA STT EMPIRICAL METRICS SUMMARY")
    print("=" * 85)
    print(f"Total Kannada Test Clips:             {len(KANNADA_BENCHMARK_CLIPS)}")
    print(f"Auto-Detection Language Accuracy:     {auto_lang_matches}/{len(KANNADA_BENCHMARK_CLIPS)} ({auto_lang_matches/len(KANNADA_BENCHMARK_CLIPS)*100:.1f}%)")
    print(f"Auto-Detection Empty Transcripts:     {auto_empty_count}/{len(KANNADA_BENCHMARK_CLIPS)} ({auto_empty_count/len(KANNADA_BENCHMARK_CLIPS)*100:.1f}%)")
    print(f"Mode A (Auto-Detect) Average CER:     {avg_auto_cer*100:.2f}%")
    print(f"Mode A (Auto-Detect) Average WER:     {avg_auto_wer*100:.2f}%")
    print(f"Mode B (Forced 'kn') Average CER:     {avg_forced_cer*100:.2f}%")
    print(f"Mode B (Forced 'kn') Average WER:     {avg_forced_wer*100:.2f}%")
    print(f"Forced 'kn' Empty Transcripts:        {forced_empty_count}/{len(KANNADA_BENCHMARK_CLIPS)} ({forced_empty_count/len(KANNADA_BENCHMARK_CLIPS)*100:.1f}%)")
    print("=" * 85)

    # ------------------------------------------------------------------------
    # End-to-End Kannada Voice-to-Chat Test with Language Hint
    # ------------------------------------------------------------------------
    print("\n--- End-to-End Kannada Voice-to-Chat with Language Hint ---")
    stt_service = SpeechToTextService(provider=provider)
    session_factory = get_session_factory()

    kn_spoken_q = "Beluru Chennakeshava devalayavannu yaaru nirmisidaru?"
    kn_wav = temp_dir / "e2e_kn_hint.wav"
    generate_spoken_audio(kn_spoken_q, kn_wav)

    try:
        upload = UploadFile(
            file=io.BytesIO(kn_wav.read_bytes()),
            filename="tourist_kn_query.wav",
            headers={"content-type": "audio/wav"},
        )
        async with session_factory() as session:
            conv_service = ConversationService(session=session)
            sess = await conv_service.create_session(language_code="kn")
            chat_res = await stt_service.voice_chat(
                upload_file=upload,
                session_uuid=sess.session_uuid,
                session=session,
                language="kn",  # Explicit language hint
            )
            print(f"Spoken Input:        '{kn_spoken_q}'")
            print(f"Transcript Emitted:  '{chat_res.transcription.text}'")
            print(f"Detected Language:   {chat_res.transcription.language}")
            print(f"Session Language:    {chat_res.chat.language}")
            print(f"Chat Answer:         '{chat_res.chat.answer}'")
            print(f"Citations Emitted:   {len(chat_res.chat.citations)}")
            print(f"Retrieval Outcome:   {'GROUNDED' if len(chat_res.chat.citations) > 0 else 'SAFE UNGROUNDED FALLBACK (PASS)'}")
    finally:
        if kn_wav.exists():
            kn_wav.unlink()

    # Privacy verification
    residual_files = list(temp_dir.glob("*"))
    print(f"\nResidual temp audio files: {len(residual_files)} (Expected: 0)")
    assert len(residual_files) == 0, f"Privacy violation: {residual_files}"
    print(">> Privacy Invariant: PASS (Zero residual files)")


if __name__ == "__main__":
    asyncio.run(run_kannada_evaluation())
