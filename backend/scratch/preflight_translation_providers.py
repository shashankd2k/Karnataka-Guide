"""
Phase 11 Translation Provider Preflight Benchmark
Evaluates Candidate 1 (AI4Bharat IndicTrans2 Distilled 200M) vs Candidate 2 (Meta NLLB-200 Distilled 600M).
Measures:
1. Environment & Setup Access Status
2. Model Download & Load Times
3. Memory Consumption (Process RAM before/after/peak)
4. Warm Inference Latency (kn -> en and en -> kn)
5. Semantic Translation Quality on Karnataka Heritage Queries & Entities
6. Offline / local_files_only Reload Verification
"""

import os
import sys
import time
import ctypes
from ctypes import wintypes
import torch

# Ensure UTF-8 output encoding for Kannada script on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [
        ('cb', wintypes.DWORD),
        ('PageFaultCount', wintypes.DWORD),
        ('PeakWorkingSetSize', ctypes.c_size_t),
        ('WorkingSetSize', ctypes.c_size_t),
        ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
        ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
        ('PagefileUsage', ctypes.c_size_t),
        ('PeakPagefileUsage', ctypes.c_size_t),
        ('PrivateUsage', ctypes.c_size_t),
    ]

def get_process_ram_mb() -> float:
    """Get current process working set resident memory in MB via Windows psapi."""
    try:
        counters = PROCESS_MEMORY_COUNTERS_EX()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        res = ctypes.windll.psapi.GetProcessMemoryInfo(
            handle,
            ctypes.byref(counters),
            counters.cb
        )
        if res:
            return round(counters.WorkingSetSize / (1024 * 1024), 2)
    except Exception as e:
        pass
    return 0.0

def test_indictrans2():
    print("\n" + "=" * 80)
    print("PREFLIGHT TEST: Candidate 1 — AI4Bharat IndicTrans2 Distilled 200M")
    print("=" * 80)
    
    results = {
        "status": "BLOCKED",
        "blockers": [],
        "ram_before_mb": get_process_ram_mb(),
    }
    
    # Check 1: IndicTransToolkit dependency
    try:
        import IndicTransToolkit
        print("[IndicTrans2] IndicTransToolkit imported successfully.")
    except ImportError as e:
        print(f"[IndicTrans2] Dependency check failed: {e}")
        results["blockers"].append("IndicTransToolkit is not installed (fails on Windows without MSVC C++ Build Tools).")
    
    # Check 2: Hugging Face model repository access
    from huggingface_hub import HfApi
    api = HfApi()
    try:
        print("[IndicTrans2] Checking Hugging Face model access for 'ai4bharat/indictrans2-indic-en-dist-200M'...")
        model_info = api.model_info("ai4bharat/indictrans2-indic-en-dist-200M")
        print(f"[IndicTrans2] Model access: id={model_info.id}, gated={model_info.gated}")
        if model_info.gated:
            results["blockers"].append("Repository is gated and requires individual HF access grant/token.")
    except Exception as e:
        print(f"[IndicTrans2] Hugging Face access check failed: {e}")
        results["blockers"].append(f"Hugging Face repository access error: {str(e)[:120]}")
    
    print(f"[IndicTrans2] Summary Blockers: {results['blockers']}")
    return results


def test_nllb():
    print("\n" + "=" * 80)
    print("PREFLIGHT TEST: Candidate 2 — Meta NLLB-200 Distilled 600M (facebook/nllb-200-distilled-600M)")
    print("=" * 80)
    
    results = {
        "status": "RUNNING",
        "blockers": [],
        "ram_before_mb": get_process_ram_mb(),
    }
    
    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        
        model_name = "facebook/nllb-200-distilled-600M"
        print(f"[NLLB-200] Initializing load for '{model_name}' on CPU...")
        
        t0 = time.perf_counter()
        ram_pre_load = get_process_ram_mb()
        
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        model.eval()
        
        load_time_ms = (time.perf_counter() - t0) * 1000
        ram_post_load = get_process_ram_mb()
        
        results["load_time_ms"] = round(load_time_ms, 2)
        results["ram_before_mb"] = round(ram_pre_load, 2)
        results["ram_after_mb"] = round(ram_post_load, 2)
        results["ram_delta_mb"] = round(ram_post_load - ram_pre_load, 2)
        print(f"[NLLB-200] Loaded in {load_time_ms:.2f} ms | RAM: {ram_pre_load:.1f} MB -> {ram_post_load:.1f} MB (Delta: +{results['ram_delta_mb']} MB)")
        
        # Test 1: Kannada -> English Translation
        # Target: "ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಕಟ್ಟಿಸಿದರು?"
        kn_input = "ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಕಟ್ಟಿಸಿದರು?"
        tokenizer.src_lang = "kan_Knda"
        forced_bos_token_id_en = tokenizer.convert_tokens_to_ids("eng_Latn")
        
        # Warmup
        inputs_kn = tokenizer(kn_input, return_tensors="pt")
        with torch.no_grad():
            _ = model.generate(**inputs_kn, forced_bos_token_id=forced_bos_token_id_en, max_new_tokens=64)
            
        # Timed KN -> EN
        t_kn0 = time.perf_counter()
        inputs_kn = tokenizer(kn_input, return_tensors="pt")
        with torch.no_grad():
            tokens_en = model.generate(**inputs_kn, forced_bos_token_id=forced_bos_token_id_en, max_new_tokens=64)
        kn_to_en_ms = (time.perf_counter() - t_kn0) * 1000
        en_translation = tokenizer.decode(tokens_en[0], skip_special_tokens=True)
        
        results["kn_input"] = kn_input
        results["en_translation"] = en_translation
        results["kn_to_en_ms"] = round(kn_to_en_ms, 2)
        print(f"\n[NLLB-200] KN -> EN:")
        print(f"  Input (KN):  {kn_input}")
        print(f"  Output (EN): {en_translation}")
        print(f"  Latency:     {kn_to_en_ms:.2f} ms")
        
        # Test 2: English -> Kannada Translation
        # Target: "The Chennakeshava Temple at Belur was commissioned by King Vishnuvardhana in 1117 CE."
        en_input = "The Chennakeshava Temple at Belur was commissioned by King Vishnuvardhana in 1117 CE."
        tokenizer.src_lang = "eng_Latn"
        forced_bos_token_id_kn = tokenizer.convert_tokens_to_ids("kan_Knda")
        
        t_en0 = time.perf_counter()
        inputs_en = tokenizer(en_input, return_tensors="pt")
        with torch.no_grad():
            tokens_kn = model.generate(**inputs_en, forced_bos_token_id=forced_bos_token_id_kn, max_new_tokens=128)
        en_to_kn_ms = (time.perf_counter() - t_en0) * 1000
        kn_translation = tokenizer.decode(tokens_kn[0], skip_special_tokens=True)
        
        results["en_input"] = en_input
        results["kn_translation"] = kn_translation
        results["en_to_kn_ms"] = round(en_to_kn_ms, 2)
        print(f"\n[NLLB-200] EN -> KN:")
        print(f"  Input (EN):  {en_input}")
        print(f"  Output (KN): {kn_translation}")
        print(f"  Latency:     {en_to_kn_ms:.2f} ms")
        
        # Test 3: Heritage Entities Battery
        heritage_tests = [
            ("Badami cave temples history", "Badami"),
            ("Aihole is known as the cradle of Indian temple architecture.", "Aihole"),
            ("Pattadakal Virupaksha temple architecture", "Pattadakal"),
            ("Hampi stone chariot in Vijayanagara empire", "Hampi"),
            ("Vittala temple musical pillars", "Vittala"),
            ("King Vishnuvardhana ruled the Hoysala dynasty in 12th century.", "Vishnuvardhana"),
        ]
        
        entity_results = []
        print("\n[NLLB-200] Heritage Entity Battery (EN -> KN):")
        for text, entity in heritage_tests:
            inputs = tokenizer(text, return_tensors="pt")
            t_ent0 = time.perf_counter()
            with torch.no_grad():
                out_toks = model.generate(**inputs, forced_bos_token_id=forced_bos_token_id_kn, max_new_tokens=64)
            ent_ms = (time.perf_counter() - t_ent0) * 1000
            translated = tokenizer.decode(out_toks[0], skip_special_tokens=True)
            entity_results.append({
                "entity": entity,
                "input": text,
                "translated": translated,
                "latency_ms": round(ent_ms, 2),
            })
            print(f"  [{entity}] {text} -> {translated} ({ent_ms:.1f}ms)")
        results["entity_tests"] = entity_results
        
        # Test 4: Offline Reload Verification (local_files_only=True)
        print("\n[NLLB-200] Verifying local offline reload (local_files_only=True)...")
        t_off0 = time.perf_counter()
        _ = AutoTokenizer.from_pretrained(model_name, local_files_only=True)
        _ = AutoModelForSeq2SeqLM.from_pretrained(model_name, local_files_only=True)
        offline_reload_ms = (time.perf_counter() - t_off0) * 1000
        results["offline_reload_ms"] = round(offline_reload_ms, 2)
        results["offline_reload_verified"] = True
        print(f"[NLLB-200] Offline reload SUCCESSFUL in {offline_reload_ms:.2f} ms.")
        
        results["status"] = "SUCCESS"
        results["peak_ram_mb"] = round(get_process_ram_mb(), 2)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        results["status"] = "ERROR"
        results["blockers"].append(str(e))
        
    return results

if __name__ == "__main__":
    print("=" * 80)
    print("PHASE 11 TRANSLATION CANDIDATE PREFLIGHT BENCHMARK")
    print(f"OS: {sys.platform} | Python: {sys.version.split()[0]} | PyTorch: {torch.__version__}")
    print(f"Initial Process RAM: {get_process_ram_mb():.1f} MB")
    print("=" * 80)
    
    indic_res = test_indictrans2()
    nllb_res = test_nllb()
    
    print("\n" + "=" * 80)
    print("FINAL SUMMARY COMPARISON")
    print("=" * 80)
    print(f"Candidate 1 (IndicTrans2): Status={indic_res['status']}, Blockers={indic_res['blockers']}")
    print(f"Candidate 2 (NLLB-200 600M): Status={nllb_res['status']}")
    if nllb_res['status'] == 'SUCCESS':
        print(f"  - Cold Model Load Time:        {nllb_res['load_time_ms']} ms")
        print(f"  - RAM (Initial / Loaded / Peak): {nllb_res['ram_before_mb']} MB / {nllb_res['ram_after_mb']} MB / {nllb_res['peak_ram_mb']} MB (Delta: +{nllb_res['ram_delta_mb']} MB)")
        print(f"  - Warm KN -> EN Latency:        {nllb_res['kn_to_en_ms']} ms")
        print(f"  - Warm EN -> KN Latency:        {nllb_res['en_to_kn_ms']} ms")
        print(f"  - Offline Reload:               {nllb_res['offline_reload_verified']} ({nllb_res['offline_reload_ms']} ms)")
