"""
Bounded live generation validation runner for Karnataka Guide.
Executes up to 5 serial requests targeting Q11/Q14 controls and Q15/Q18 failures.
Captures exact prompts, effective options, raw & sanitized output, and finish/token telemetry.
Persists every attempt immediately to JSONL.
Enforces a 1-timeout circuit breaker.
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"D:\Karnataka Guide\backend")
import asyncio
import json
import os
import re
import time
from typing import Dict, Any, List
import httpx

from app.application.rag.schemas import RetrievalCandidate
from app.application.rag.prompt_builder import (
    build_grounded_prompt,
    select_grounded_candidates,
)
from app.application.conversation.citation_formatter import (
    extract_authoritative_citations,
    sanitize_model_citations,
    filter_authoritative_citations,
)

OLLAMA_BASE_URL = "http://127.0.0.1:11434"
MODEL_NAME = "phi3:mini"
TIMEOUT_SECONDS = 90.0
MAX_LIVE_REQUESTS = 8
ACTIVE_GEN_ID = "1a2c6365-1bee-4478-9599-a706ee5c7221"

JSONL_OUTPUT_PATH = r"D:\Karnataka Guide\evidence\20260927_recovery_answer_validation\live_generation_validation_results.jsonl"

DOC_MAPPING = {
    "1f638186-c23e-489e-9bf2-7d675191f2ac.pdf": "Belur_Halebidu_Hoysala_Guide.pdf",
    "cc5d7b4e-2ddc-428d-81b4-89acaf2c33f7.pdf": "Badami_Caves_Guide.pdf",
    "7d87519a-9315-47e9-864b-2dc2f590df78.pdf": "Aihole_Heritage_Guide.pdf",
    "b40b9e04-bc95-4789-8059-cac917c1d073.pdf": "Pattadakal_UNESCO_Guide.pdf",
}

def extract_candidates_from_reconstructed(query_entry: Dict[str, Any]) -> List[RetrievalCandidate]:
    user_prompt = query_entry["user_prompt"]
    cits = query_entry["authoritative_citations"]
    ev_text = user_prompt.split("=== EVIDENCE START ===\n")[1].split("\n=== EVIDENCE END ===")[0]
    chunks = re.split(r"\n\n(?=\[\d+\] \(Source:)", ev_text)

    candidates = []
    for i, chunk_block in enumerate(chunks):
        lines = chunk_block.split("\n")
        header = lines[0]
        text = "\n".join(lines[1:]).strip()

        cit_meta = cits[i] if i < len(cits) else {}
        orig_filename = DOC_MAPPING.get(cit_meta.get("source_filename"), cit_meta.get("source_filename", "guide.pdf"))

        cand = RetrievalCandidate(
            chunk_id=cit_meta.get("chunk_id", f"chk-{i+1}"),
            document_id=cit_meta.get("document_id", "doc-1"),
            generation_id=ACTIVE_GEN_ID,
            text=text,
            page_number=cit_meta.get("page_number", 1),
            source_filename=orig_filename,
            section=cit_meta.get("section_header"),
            reranker_score=cit_meta.get("reranker_score", 1.0),
            final_rank=i + 1,
        )
        candidates.append(cand)
    return candidates


async def run_single_request(
    client: httpx.AsyncClient,
    request_num: int,
    qid: str,
    arm: str,
    query_text: str,
    candidates: List[RetrievalCandidate],
) -> Dict[str, Any]:
    sys_prompt, user_prompt, auth_labels = build_grounded_prompt(
        query=query_text,
        candidates=candidates,
        language="en",
        max_chars=2000,
    )

    accepted = select_grounded_candidates(candidates, max_chars=2000, max_passages=2)
    auth_citations = extract_authoritative_citations(
        candidates=accepted,
        active_generation_id=ACTIVE_GEN_ID,
        max_passages=len(accepted),
    )

    options = {
        "temperature": 0.1,
        "top_p": 0.9,
        "num_predict": 128,
        "num_ctx": 1536,
        "num_thread": 2,
        "stop": ["\n\n", "###", "\nTourist Question:", "\nTourist:", "\nUser:", "\nAssistant:", "\nQuestion:"],
    }

    payload = {
        "model": MODEL_NAME,
        "system": sys_prompt,
        "prompt": user_prompt,
        "stream": False,
        "keep_alive": "10m",
        "options": options,
    }

    t0 = time.perf_counter()
    raw_answer = ""
    error_msg = None
    telemetry = {}

    try:
        resp = await client.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=TIMEOUT_SECONDS,
        )
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        resp.raise_for_status()
        data = resp.json()
        raw_answer = data.get("response", "").strip()

        telemetry = {
            "done": data.get("done"),
            "done_reason": data.get("done_reason"),
            "total_duration_ns": data.get("total_duration"),
            "load_duration_ns": data.get("load_duration"),
            "prompt_eval_count": data.get("prompt_eval_count"),
            "prompt_eval_duration_ns": data.get("prompt_eval_duration"),
            "eval_count": data.get("eval_count"),
            "eval_duration_ns": data.get("eval_duration"),
        }

    except httpx.TimeoutException:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        error_msg = f"TIMEOUT: Request timed out after {TIMEOUT_SECONDS}s"
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        error_msg = f"ERROR: {type(exc).__name__}: {str(exc)}"

    sanitized = sanitize_model_citations(raw_answer, auth_labels) if raw_answer else ""
    public_cits = filter_authoritative_citations(sanitized, auth_citations, public_only=True) if sanitized else []

    record = {
        "request_index": request_num,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "query_id": qid,
        "arm": arm,
        "query_text": query_text,
        "effective_options": options,
        "authorized_labels": auth_labels,
        "accepted_candidates_count": len(accepted),
        "system_prompt": sys_prompt,
        "user_prompt": user_prompt,
        "raw_response": raw_answer,
        "sanitized_response": sanitized,
        "citations_emitted": public_cits,
        "elapsed_ms": elapsed_ms,
        "telemetry": telemetry,
        "error": error_msg,
    }

    # Persist immediately to JSONL
    with open(JSONL_OUTPUT_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return record


async def main():
    print("=" * 80)
    print("STARTING BOUNDED LIVE GENERATION VALIDATION")
    print(f"Model: {MODEL_NAME} | Context Budget: 2000 chars | Token limit: 128")
    print(f"Targeting Q11, Q14 controls and Q15, Q18 failures (Max requests: {MAX_LIVE_REQUESTS})")
    print(f"Persisting to: {JSONL_OUTPUT_PATH}")
    print("=" * 80)

    # Initialize empty or clear existing JSONL for this run
    if os.path.exists(JSONL_OUTPUT_PATH):
        os.remove(JSONL_OUTPUT_PATH)

    recon_data = json.load(open("evidence/20260927_recovery_answer_validation/reconstructed_production_inputs_all24.json", encoding="utf-8"))

    plan = [
        ("Q11", "arm_15", "Q11 Halebidu 8 relief friezes (Arm 15 control)"),
        ("Q14", "arm_15", "Q14 Hoysala stone material (Arm 15 control)"),
        ("Q14", "arm_10", "Q14 Hoysala stone material (Arm 10 comparison)"),
        ("Q15", "arm_15", "Q15 Badami Cave 4 Mahavira/Bahubali (Arm 15 failure case)"),
        ("Q18", "arm_15", "Q18 Aihole Lad Khan timber joinery (Arm 15 failure case)"),
    ]

    async with httpx.AsyncClient() as client:
        # Check health first
        h_resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
        if h_resp.status_code != 200:
            print(f"ABORT: Ollama health check returned {h_resp.status_code}")
            return

        request_count = 0
        for qid, arm, desc in plan:
            if request_count >= MAX_LIVE_REQUESTS:
                print(f"Reached maximum request budget ({MAX_LIVE_REQUESTS}). Stopping.")
                break

            request_count += 1
            print(f"\n[{request_count}/{len(plan)}] Executing: {desc}")
            q_entry = recon_data["queries"][qid][arm]
            query_text = recon_data["queries"][qid]["query_text"]
            candidates = extract_candidates_from_reconstructed(q_entry)

            rec = await run_single_request(
                client=client,
                request_num=request_count,
                qid=qid,
                arm=arm,
                query_text=query_text,
                candidates=candidates,
            )

            if rec["error"]:
                print(f"  FAILED: {rec['error']}")
                print("  CIRCUIT BREAKER: Aborting further live requests due to error/timeout.")
                break
            else:
                print(f"  Elapsed: {rec['elapsed_ms']} ms | Tokens: {rec['telemetry'].get('eval_count')} | Done: {rec['telemetry'].get('done_reason')}")
                print(f"  Raw: {rec['raw_response']}")
                print(f"  Sanitized: {rec['sanitized_response']}")
                print(f"  Citations: {[c['citation_label'] + ' ' + c['source_filename'] for c in rec['citations_emitted']]}")

    print("\n" + "=" * 80)
    print(f"COMPLETED {request_count} LIVE GENERATION REQUESTS")
    print(f"Saved to: {JSONL_OUTPUT_PATH}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
