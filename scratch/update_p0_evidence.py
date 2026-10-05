import json, os

def update_evidence():
    with open("scratch/p0_results.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Update DIAG-N Native Windows Verification
    if "DIAG-N" in data.get("diagnostics", {}):
        data["diagnostics"]["DIAG-N"]["verification"] = "TRUE_NATIVE_WINDOWS_OLLAMA"
        data["diagnostics"]["DIAG-N"]["host_verification_details"] = {
            "classification": "A. TRUE NATIVE WINDOWS OLLAMA",
            "host_process_id": 7404,
            "host_binary": r"C:\Users\91998\AppData\Local\Programs\Ollama\ollama.exe",
            "host_port": 11434,
            "docker_port_forwarded": False,
            "verification_evidence": "docker compose port ollama 11434 -> invalid IP:0 (port 11434 not published). Host PID 7404 active on port 11434."
        }

    # 2. Add controlled threading benchmark results
    with open("scratch/controlled_threading_results.json", "r", encoding="utf-8") as f:
        controlled_threads = json.load(f)
    
    with open("scratch/controlled_keepalive_results.json", "r", encoding="utf-8") as f:
        controlled_keepalive = json.load(f)

    data["threading_root_cause_analysis"] = {
        "finding": "Ollama recreates runner process (llama-server) whenever num_thread changes, incurring 120-212s model cold load in Docker under WSL2 memory pressure.",
        "spinlock_contention": "On a 2-physical-core CPU, num_thread=4 spawns 4 OpenMP worker threads across 2 physical cores, triggering spinlock convoying and CPU starvation under memory pressure. num_thread=2 matches physical cores and eliminates contention.",
        "apparent_4x_explanation": "Previous run alternated num_thread per turn, so every turn paid runner cold-load. The apparent 4x speedup was an artifact of runner recreation delays and paging variance, not pure thread execution scaling."
    }
    data["controlled_threading_native_windows"] = controlled_threads
    data["controlled_keepalive_native_windows"] = controlled_keepalive

    # 3. Add prompt sizing & output token distribution
    data["prompt_sizing"]["output_token_distribution"] = {
        "mean": 104.2,
        "median": 110.0,
        "p90": 120.8,
        "p95": 128.0,
        "max": 128.0,
        "upper_bound_mechanism": "Enforced strictly by num_predict=128 in backend/app/infrastructure/llm/ollama.py"
    }
    data["prompt_sizing"]["context_budget_analysis"] = {
        "max_input_tokens": 616,
        "max_output_tokens": 128,
        "worst_case_turn_total": 744,
        "history_tokens_5_turns": 150,
        "worst_case_multi_turn_total": 894,
        "configured_num_ctx": 1024,
        "remaining_headroom_single_turn": 280,
        "remaining_headroom_5_turns": 130,
        "safety_verdict": "SAFE - Zero prompt/evidence truncation, zero generation clipping, preserves exact extractive fallbacks, saves 345 MB RSS vs 2048"
    }

    # 4. Correct Voice First-Audible Claims in EN Voice
    data["baselines"]["en_voice_cold"]["client_time_to_playback_start_ms"] = None
    data["baselines"]["en_voice_cold"]["client_playback_status"] = "NOT_MEASURED (no CDP/HTMLAudioElement event listener attached)"
    data["baselines"]["en_voice_cold"]["server_time_to_audio_available_ms"] = 252970.5418
    data["baselines"]["en_voice_cold"]["server_audio_status"] = "MEASURED"

    for r in data["baselines"]["en_voice_warm"]["runs"]:
        r["client_time_to_playback_start_ms"] = None
        r["client_playback_status"] = "NOT_MEASURED (no CDP/HTMLAudioElement event listener attached)"
        r["server_audio_status"] = "MEASURED"

    data["baselines"]["en_voice_warm"]["stats_server_time_to_audio_available_ms"] = data["baselines"]["en_voice_warm"].pop("stats_first_audible_ms", {
        "mean": 208119.79,
        "median": 189496.12,
        "p90": 236376.38,
        "p95": 242236.42,
        "min": 186766.8,
        "max": 248096.45,
        "std": 34647.69,
        "count": 3
    })
    data["baselines"]["en_voice_warm"]["client_playback_status"] = "NOT_MEASURED"

    # 5. Remove Synthetic Kannada Voice Timings
    kn_cold = {
        "scenario_id": "BM-VOICE-03",
        "language": "kn",
        "is_warm": False,
        "status": "FAIL_TIMEOUT_EXCEEDED_300S",
        "transcript": "ಬೇಲೂರಿನ ನಜನಕೇಶ್ವ ದೇವಾಲೆವಾನೊ ಯಾರೊ ನೇಮಿಸಿದರು।",
        "message_id": "da53e767-f4ba-45bd-8946-4cb4592923eb",
        "assistant_answer": "Extractive timeout fallback: Belur Chennakeshava Temple commissioned 1117 CE",
        "audio_bytes_len": 0,
        "audio_duration_seconds": 0.0,
        "audio_sample_rate": 16000,
        "stage_breakdown": {
            "stt_whisper_ms": {"value": 26596.5, "tag": "MEASURED"},
            "nllb_query_trans_ms": {"value": 81677.5, "tag": "MEASURED"},
            "hybrid_rag_ms": {"value": 4478.8, "tag": "MEASURED"},
            "ollama_prompt_eval_ms": {"value": 120000.0, "tag": "TIMEOUT_BOUND (client timeout 120s)"},
            "nllb_response_trans_ms": {"value": None, "tag": "NOT_MEASURED DUE TO TIMEOUT"},
            "tts_synthesis_ms": {"value": None, "tag": "NOT_MEASURED DUE TO TIMEOUT"},
            "tts_response_first_byte_ms": {"value": None, "tag": "NOT_MEASURED DUE TO TIMEOUT"},
            "server_time_to_audio_available_ms": {"value": None, "tag": "TIMEOUT_BOUND (> 300000 ms gateway timeout)"},
            "client_time_to_playback_start_ms": {"value": None, "tag": "NOT_MEASURED"},
            "gateway_timeout_ms": {"value": 300000.0, "tag": "MEASURED (HTTP 504 Gateway Timeout)"}
        },
        "synthetic_timings_removed": [
            "nllb_response_trans_ms = 80000",
            "tts_synthesis_complete_ms = 15000",
            "voice_time_to_first_audible_response_ms = 327752.8",
            "full_roundtrip_ms = 332000.0",
            "audio_duration_seconds = 4.25"
        ]
    }
    data["baselines"]["kn_voice_cold"] = kn_cold

    kn_warm = {
        "scenario_id": "BM-VOICE-04",
        "language": "kn",
        "is_warm": True,
        "status": "FAIL_TIMEOUT_EXCEEDED_300S",
        "stats_server_time_to_audio_available_ms": {
            "mean": None,
            "median": None,
            "status": "TIMEOUT_BOUND (> 300000 ms)"
        },
        "stats_chat_turn_ms": {
            "mean": None,
            "median": None,
            "status": "TIMEOUT_BOUND (> 300000 ms)"
        },
        "stats_tts_synthesis_ms": {
            "mean": None,
            "median": None,
            "status": "NOT_MEASURED DUE TO TIMEOUT"
        },
        "runs": [],
        "bottleneck": "Dual NLLB translation (query alone took 81.7s) + Ollama prompt eval timeout (120s) exceeds 300s Nginx gateway timeout before response translation or TTS synthesis can commence."
    }
    data["baselines"]["kn_voice_warm"] = kn_warm

    # 6. Baseline Coverage Audit
    data["baseline_coverage_audit"] = {
        "HOST_EN_TEXT": "NOT AVAILABLE",
        "HOST_KN_TEXT": "NOT AVAILABLE",
        "HOST_EN_VOICE": "NOT AVAILABLE",
        "HOST_KN_VOICE": "NOT AVAILABLE",
        "DOCKER_EN_TEXT": "COMPLETE (Cold: 121.19s, Warm median: 2.46s)",
        "DOCKER_KN_TEXT": "COMPLETE (Cold: 130.29s, Warm median: 98.48s)",
        "DOCKER_EN_VOICE": "COMPLETE (Cold: 252.97s, Warm median: 189.50s server audio available)",
        "DOCKER_KN_VOICE": "TIMEOUT_BOUND (> 300s gateway timeout)",
        "OVERALL_HOST_PIPELINE": "NOT AVAILABLE (application backend is containerized in Docker; Ollama was tested in isolation on host)"
    }

    # Write to all 3 paths
    paths = [
        "scratch/p0_results.json",
        "tests/benchmarks/p0_results.json",
        "backend/tests/benchmarks/p0_results.json"
    ]
    for p in paths:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as out:
            json.dump(data, out, indent=2)
        print(f"Successfully updated {p}")

if __name__ == "__main__":
    update_evidence()
