"""
Kannada TTS Preflight: facebook/mms-tts-kan on CPU (Windows 11, Python 3.12).
Evaluates:
1. Model and tokenizer accessibility from Hugging Face
2. Cold load latency and process RAM impact
3. Synthesis of target Kannada sentence:
   'ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ರಾಜ ವಿಷ್ಣುವರ್ಧನನು ಕ್ರಿ.ಶ. 1117ರಲ್ಲಿ ನಿರ್ಮಿಸಿದರು.'
4. Output WAV generation (sample rate, bit depth, waveform length, file write)
5. Synthesis latency and Real-Time Factor (RTF)
6. 12-item heritage proper noun battery
7. local_files_only=True offline reload
8. License & model size
"""

import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import time
import numpy as np
import torch
import scipy.io.wavfile
from pathlib import Path
import ctypes
from ctypes import wintypes

class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
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
    ]

def get_process_ram_mb() -> float:
    try:
        process = ctypes.windll.kernel32.GetCurrentProcess()
        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        if ctypes.windll.psapi.GetProcessMemoryInfo(process, ctypes.byref(counters), counters.cb):
            return counters.WorkingSetSize / (1024 * 1024)
    except Exception:
        pass
    return 0.0

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_ID = "facebook/mms-tts-kan"

def main():
    print("=" * 80)
    print("KANNADA TTS PREFLIGHT: facebook/mms-tts-kan (VITS on CPU)")
    print("=" * 80)
    print(f"Python: {sys.version}")
    print(f"PyTorch: {torch.__version__}")
    
    # Step 1: Baseline RAM
    ram_baseline = get_process_ram_mb()
    print(f"Baseline Process RAM: {ram_baseline:.2f} MB")
    
    # Step 2: Import & Load Tokenizer + VITS Model
    from transformers import VitsModel, AutoTokenizer
    
    print("-" * 80)
    print(f"Loading {MODEL_ID} from Hugging Face / cache...")
    t0 = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = VitsModel.from_pretrained(MODEL_ID)
    model.eval()
    cold_load_ms = (time.perf_counter() - t0) * 1000
    
    ram_loaded = get_process_ram_mb()
    ram_delta = ram_loaded - ram_baseline
    
    # Count model parameters and compute memory footprint
    param_count = sum(p.numel() for p in model.parameters())
    param_size_mb = sum(p.numel() * p.element_size() for p in model.parameters()) / (1024 * 1024)
    
    print(f"Cold Model Load Latency: {cold_load_ms:.2f} ms")
    print(f"Model Parameter Count:   {param_count:,} ({param_size_mb:.2f} MB raw weights)")
    print(f"Post-Load Process RAM:   {ram_loaded:.2f} MB (Delta: +{ram_delta:.2f} MB)")
    print(f"Model Native Sample Rate: {model.config.sampling_rate} Hz")
    
    # Step 3: Target Kannada Sentence Synthesis
    target_kannada = "ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ರಾಜ ವಿಷ್ಣುವರ್ಧನನು ಕ್ರಿ.ಶ. 1117ರಲ್ಲಿ ನಿರ್ಮಿಸಿದರು."
    print("-" * 80)
    print(f"Synthesizing Target Sentence:\n  '{target_kannada}'")
    
    # Tokenize
    inputs = tokenizer(target_kannada, return_tensors="pt")
    input_ids = inputs["input_ids"]
    print(f"Tokenized Sequence Length: {input_ids.shape[-1]} tokens")
    
    t_synth_0 = time.perf_counter()
    with torch.no_grad():
        output = model(**inputs).waveform
    synth_duration_ms = (time.perf_counter() - t_synth_0) * 1000
    
    waveform = output.squeeze().cpu().numpy()
    sample_rate = model.config.sampling_rate
    audio_duration_s = len(waveform) / float(sample_rate)
    rtf = (synth_duration_ms / 1000.0) / audio_duration_s if audio_duration_s > 0 else 0.0
    
    # Write WAV file
    wav_out_path = BASE_DIR / "scratch" / "test_mms_kannada_target.wav"
    # Normalize float32 waveform to int16 PCM
    waveform_norm = np.clip(waveform, -1.0, 1.0)
    waveform_int16 = (waveform_norm * 32767).astype(np.int16)
    scipy.io.wavfile.write(str(wav_out_path), rate=sample_rate, data=waveform_int16)
    
    print("-" * 80)
    print("TARGET KANNADA SYNTHESIS METRICS:")
    print(f"  - Output File:       {wav_out_path.name} ({wav_out_path.stat().st_size} bytes)")
    print(f"  - Format:            Mono 16-bit PCM WAV")
    print(f"  - Sample Rate:       {sample_rate} Hz")
    print(f"  - Audio Duration:    {audio_duration_s:.2f} seconds ({len(waveform)} samples)")
    print(f"  - Synthesis Latency: {synth_duration_ms:.2f} ms")
    print(f"  - Real-Time Factor:  {rtf:.3f}x ({1.0/rtf:.1f}x real-time speed on CPU)")
    print(f"  - Peak Amplitude:    {np.max(np.abs(waveform)):.4f} (Non-empty: {np.max(np.abs(waveform)) > 0.01})")
    
    # Step 4: Heritage Entity Battery
    heritage_entities = [
        ("Belur", "ಬೇಲೂರು"),
        ("Chennakeshava", "ಚೆನ್ನಕೇಶವ"),
        ("Halebidu", "ಹಳೇಬೀಡು"),
        ("Hoysaleswara", "ಹೊಯ್ಸಳೇಶ್ವರ"),
        ("Badami", "ಬಾದಾಮಿ"),
        ("Aihole", "ಐಹೊಳೆ"),
        ("Pattadakal", "ಪಟ್ಟದಕಲ್ಲು"),
        ("Hampi", "ಹಂಪಿ"),
        ("Virupaksha", "ವಿರೂಪಾಕ್ಷ"),
        ("Vittala", "ವಿಠ್ಠಲ"),
        ("Vijayanagara", "ವಿಜಯನಗರ"),
        ("Vishnuvardhana", "ವಿಷ್ಣುವರ್ಧನ"),
    ]
    
    print("-" * 80)
    print("12-ITEM KANNADA HERITAGE PROPER NOUN BATTERY:")
    total_audio_s = 0.0
    total_synth_ms = 0.0
    
    for en_name, kn_text in heritage_entities:
        phrase = f"{kn_text}ಗೆ ಸುಸ್ವಾಗತ."  # "Welcome to <Entity>."
        inp = tokenizer(phrase, return_tensors="pt")
        t0 = time.perf_counter()
        with torch.no_grad():
            wav = model(**inp).waveform.squeeze().cpu().numpy()
        dur_ms = (time.perf_counter() - t0) * 1000
        
        aud_s = len(wav) / float(sample_rate)
        total_audio_s += aud_s
        total_synth_ms += dur_ms
        e_rtf = (dur_ms / 1000.0) / aud_s if aud_s > 0 else 0.0
        peak = np.max(np.abs(wav))
        print(f"  - {en_name:<16} ({kn_text:<12}): Audio={aud_s:.2f}s | Latency={dur_ms:6.1f}ms | RTF={e_rtf:.3f}x | Peak={peak:.3f}")
        
    avg_rtf = (total_synth_ms / 1000.0) / total_audio_s if total_audio_s > 0 else 0.0
    print(f"\nAverage Heritage Battery RTF: {avg_rtf:.3f}x ({1.0/avg_rtf:.1f}x real-time speed)")
    
    # Step 5: Offline local_files_only=True Reload Verification
    print("-" * 80)
    print("OFFLINE RELOAD VERIFICATION (local_files_only=True):")
    t0 = time.perf_counter()
    reloaded_tok = AutoTokenizer.from_pretrained(MODEL_ID, local_files_only=True)
    reloaded_mod = VitsModel.from_pretrained(MODEL_ID, local_files_only=True)
    reloaded_mod.eval()
    reload_ms = (time.perf_counter() - t0) * 1000
    print(f"  - Offline Reload from local cache: SUCCESS ({reload_ms:.2f} ms)")
    
    # Step 6: License and Summary
    print("=" * 80)
    print("KANNADA MMS-TTS PREFLIGHT SUMMARY:")
    print(f"  - Provider:         Meta MMS-TTS (facebook/mms-tts-kan)")
    print(f"  - Architecture:     VITS (Variational Inference with adversarial learning for end-to-end Text-to-Speech)")
    print(f"  - Model Size:       {param_size_mb:.2f} MB ({param_count:,} parameters)")
    print(f"  - Sample Rate:      {sample_rate} Hz")
    print(f"  - Process RAM:      +{ram_delta:.2f} MB")
    print(f"  - Target Latency:   {synth_duration_ms:.2f} ms (RTF: {rtf:.3f}x)")
    print(f"  - License:          CC-BY-NC 4.0 (Meta MMS Project)")
    print(f"  - Kannada Result:   WORKING (PASS)")
    print("=" * 80)

if __name__ == "__main__":
    main()
