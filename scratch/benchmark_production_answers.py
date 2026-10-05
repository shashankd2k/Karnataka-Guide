import asyncio
import json
import re
import urllib.request
import time
import statistics
from typing import Dict, List, Any

from app.infrastructure.db.session import get_session_factory
from app.infrastructure.db.models.generation import KnowledgeGeneration
from app.application.conversation.language_detector import detect_language
from app.application.conversation.grounding_guard import GroundingGuard
from app.application.rag.service import RAGRetrievalService
from app.application.rag.schemas import RetrievalDiagnosticRequest
from app.application.rag.prompt_builder import build_grounded_prompt
from app.application.conversation.citation_formatter import sanitize_model_citations
from app.application.translation.service import TranslationService
from app.core.config import get_settings
from sqlalchemy import select

PROMPTS = [
    {"id": "P01", "query": "Who commissioned the Chennakeshava Temple at Belur and when?"},
    {"id": "P02", "query": "What are the major architectural features of the Chennakeshava temple?"},
    {"id": "P03", "query": "Describe the bracket figures (Madanikas) found at Belur."},
    {"id": "P04", "query": "What stone was used in the construction of Belur temple?"},
    {"id": "P05", "query": "What are the visiting hours and entry fees for Belur Chennakeshava temple?"},
    {"id": "P06", "query": "What is the significance of Hoysaleswara Temple at Halebidu?"},
    {"id": "P07", "query": "Why was the Hoysaleswara temple left incomplete?"},
    {"id": "P08", "query": "Explain the friezes of elephants, lions, and horses at Halebidu."},
    {"id": "P09", "query": "Are there Jain temples near Halebidu complex?"},
    {"id": "P10", "query": "How far is Halebidu from Belur and how can tourists travel between them?"},
    {"id": "P11", "query": "Tell me about the Vijayanagara empire capital at Hampi."},
    {"id": "P12", "query": "What is unique about the musical pillars in Vittala Temple Hampi?"},
    {"id": "P13", "query": "Describe the stone chariot at the Vittala temple complex."},
    {"id": "P14", "query": "What is the history of the Virupaksha Temple on Hemakuta hill?"},
    {"id": "P15", "query": "What are the best viewpoints to watch sunset in Hampi?"},
    {"id": "P16", "query": "Describe the rock-cut cave temples of Badami and their presiding deities."},
    {"id": "P17", "query": "What is the architectural significance of the Pattadakal group of monuments?"},
    {"id": "P18", "query": "Why is Aihole considered the cradle of Indian temple architecture?"},
    {"id": "P19", "query": "Explain the apsidal plan of the Durga Temple at Aihole."},
    {"id": "P20", "query": "What are the differences between northern Rekha-Nagara and southern Dravida styles at Pattadakal?"},
    {"id": "P21", "query": "Can you tell me about the kings who patronized these temples?"},
    {"id": "P22", "query": "What was the battle of Talikota and how did it affect Hampi?"},
    {"id": "P23", "query": "Are photography and videography permitted inside the sanctum sanctorum?"},
    {"id": "P24", "query": "What is the best season of the year to visit Karnataka heritage sites?"},
    {"id": "P25", "query": "Are there guided audio tours or authorized ASI guides available at Belur?"},
    {"id": "P26", "query": "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ನಿರ್ಮಿಸಿದರು?"},
    {"id": "P27", "query": "ಹಳೆಬೀಡಿನ ಹೊಯ್ಸಳೇಶ್ವರ ದೇವಾಲಯದ ವಿಶೇಷತೆಗಳೇನು?"},
    {"id": "P28", "query": "ಹಂಪಿಯ ವಿರೂಪಾಕ್ಷ ದೇವಾಲಯದ ಇತಿಹಾಸವನ್ನು ತಿಳಿಸಿ."},
    {"id": "P29", "query": "Namaskara! Can you help plan my weekend tour to Hassan district?"},
    {"id": "P30", "query": "What is the distance between Eiffel Tower and Belur Temple?"},
]

TERMINAL_PUNCTUATION_REGEX = re.compile(r'[\.\!\?।]["\']?\s*$')

def check_sentence_completion(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return False
    # If ends with bracketed citation [1]. or [1]
    if re.search(r'\[\d+\]\s*[\.\!\?।]?\s*$', cleaned):
        return True
    return bool(TERMINAL_PUNCTUATION_REGEX.search(cleaned))

def call_ollama(system_prompt: str, user_prompt: str, num_predict: int = 128) -> Dict[str, Any]:
    options = {
        "num_ctx": 1024,
        "num_predict": num_predict,
        "temperature": 0.1,
    }
    payload = {
        "model": "phi3:mini",
        "system": system_prompt,
        "prompt": user_prompt,
        "stream": False,
        "keep_alive": "10m",
        "options": options
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request("http://ollama:11434/api/generate", data=data, headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=180) as resp:
        res = json.loads(resp.read().decode())
    res["wall_ms"] = (time.perf_counter() - t0) * 1000
    return res

async def main():
    settings = get_settings()
    factory = get_session_factory()
    grounding_guard = GroundingGuard(min_score_threshold=settings.CONVERSATION_GROUNDING_MIN_SCORE)
    translation_service = TranslationService()

    results_prod = []
    results_diag_natural = []

    print("=" * 85)
    print("RUNNING REAL PRODUCTION-ANSWER OUTPUT-LENGTH BENCHMARK (30 QUERIES)")
    print("=" * 85)

    async with factory() as db_session:
        # Verify active generation
        gen_stmt = select(KnowledgeGeneration).where(KnowledgeGeneration.is_active == True)
        gen = (await db_session.execute(gen_stmt)).scalar_one_or_none()
        print(f"Active Knowledge Generation: {gen.id} ({gen.generation_version})")

        rag_service = RAGRetrievalService(session=db_session)

        for item in PROMPTS:
            qid = item["id"]
            raw_query = item["query"]
            lang_res = detect_language(raw_query)
            effective_lang = lang_res.language if lang_res.language in ("kn", "en") else "en"

            # 1. Translate query if Kannada
            if effective_lang == "kn":
                search_query = await translation_service.translate_retrieval_query(raw_query, from_lang="kn", to_lang="en")
            else:
                search_query = raw_query

            # 2. Retrieve evidence
            req = RetrievalDiagnosticRequest(
                query=search_query,
                top_k=settings.RETRIEVAL_FINAL_TOP_K,
                dense_top_k=settings.RETRIEVAL_DENSE_TOP_K,
                bm25_top_k=settings.RETRIEVAL_BM25_TOP_K,
                rerank_candidates=settings.RETRIEVAL_RERANK_CANDIDATES,
                enable_reranker=True,
                filter_noise=True,
                suppress_duplicates=True,
            )
            retrieval_resp = await rag_service.retrieve_evidence(req)

            # 3. Grounding evaluation
            grounding_result = grounding_guard.evaluate(
                candidates=retrieval_resp.results,
                language=effective_lang,
                active_generation_id=retrieval_resp.active_generation_id,
            )

            # 4. Handle ungrounded / fallback
            if not grounding_result.is_grounded or not retrieval_resp.results:
                exact_fallback = "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ." if effective_lang == "kn" else "Information is not available in the knowledge base."
                fallback_tokens = len(exact_fallback.split())  # approximate token length
                record_prod = {
                    "id": qid,
                    "query": raw_query,
                    "language": effective_lang,
                    "grounded": False,
                    "input_tokens": 0,
                    "generated_output_tokens": fallback_tokens,
                    "finish_reason": "ungrounded_fallback",
                    "ends_in_complete_sentence": True,
                    "reached_num_predict": False,
                    "appears_truncated": False,
                    "answer": exact_fallback,
                }
                record_diag = dict(record_prod)
            else:
                # 5. Build prompt
                sys_prompt, user_prompt, auth_labels = build_grounded_prompt(
                    query=search_query,
                    candidates=retrieval_resp.results,
                    language="en",
                    max_chars=settings.OLLAMA_MAX_CONTEXT_CHARS,
                )

                # 6. Production run with num_predict=128
                resp_128 = call_ollama(sys_prompt, user_prompt, num_predict=128)
                raw_ans_128 = resp_128.get("response", "").strip()
                ans_128 = sanitize_model_citations(raw_ans_128, auth_labels)
                eval_cnt_128 = resp_128.get("eval_count", 0)
                peval_cnt_128 = resp_128.get("prompt_eval_count", 0)
                done_reason_128 = resp_128.get("done_reason", "stop")
                complete_128 = check_sentence_completion(raw_ans_128)
                reached_128 = (eval_cnt_128 == 128)
                truncated_128 = (reached_128 and not complete_128) or (not complete_128)

                record_prod = {
                    "id": qid,
                    "query": raw_query,
                    "language": effective_lang,
                    "grounded": True,
                    "input_tokens": peval_cnt_128,
                    "generated_output_tokens": eval_cnt_128,
                    "finish_reason": done_reason_128,
                    "ends_in_complete_sentence": complete_128,
                    "reached_num_predict": reached_128,
                    "appears_truncated": truncated_128,
                    "answer_preview": (ans_128[:80] + "...") if len(ans_128) > 80 else ans_128,
                }

                # 7. Diagnostic unconstrained run with num_predict=256
                resp_256 = call_ollama(sys_prompt, user_prompt, num_predict=256)
                raw_ans_256 = resp_256.get("response", "").strip()
                ans_256 = sanitize_model_citations(raw_ans_256, auth_labels)
                eval_cnt_256 = resp_256.get("eval_count", 0)
                peval_cnt_256 = resp_256.get("prompt_eval_count", 0)
                done_reason_256 = resp_256.get("done_reason", "stop")
                complete_256 = check_sentence_completion(raw_ans_256)
                reached_256 = (eval_cnt_256 == 256)
                truncated_256 = (reached_256 and not complete_256) or (not complete_256)

                record_diag = {
                    "id": qid,
                    "query": raw_query,
                    "language": effective_lang,
                    "grounded": True,
                    "input_tokens": peval_cnt_256,
                    "generated_output_tokens": eval_cnt_256,
                    "finish_reason": done_reason_256,
                    "ends_in_complete_sentence": complete_256,
                    "reached_num_predict": reached_256,
                    "appears_truncated": truncated_256,
                    "answer_preview": (ans_256[:80] + "...") if len(ans_256) > 80 else ans_256,
                }

            results_prod.append(record_prod)
            results_diag_natural.append(record_diag)
            print(f"[{qid}] In: {record_prod['input_tokens']} tok | Out(128): {record_prod['generated_output_tokens']} tok (complete: {record_prod['ends_in_complete_sentence']}) | Out(256): {record_diag['generated_output_tokens']} tok (complete: {record_diag['ends_in_complete_sentence']})")

    # Compute percentiles for production (128 cap)
    out_tokens_128 = [r["generated_output_tokens"] for r in results_prod if r["grounded"]]
    out_tokens_diag = [r["generated_output_tokens"] for r in results_diag_natural if r["grounded"]]
    in_tokens = [r["input_tokens"] for r in results_prod if r["grounded"]]

    def get_stats(data):
        s = sorted(data)
        n = len(s)
        p50 = statistics.median(s)
        p90 = s[int(0.90 * (n - 1))]
        p95 = s[int(0.95 * (n - 1))]
        max_val = max(s)
        mean_val = round(statistics.mean(s), 2)
        return {"mean": mean_val, "p50": p50, "p90": p90, "p95": p95, "max": max_val}

    stats_out_128 = get_stats(out_tokens_128)
    stats_out_diag = get_stats(out_tokens_diag)
    stats_in = get_stats(in_tokens)

    hits_cap_128 = sum(1 for r in results_prod if r["reached_num_predict"])
    truncated_cnt_128 = sum(1 for r in results_prod if r["appears_truncated"])
    hits_cap_diag = sum(1 for r in results_diag_natural if r["reached_num_predict"])
    truncated_cnt_diag = sum(1 for r in results_diag_natural if r["appears_truncated"])

    summary = {
        "production_128_cap": {
            "output_stats": stats_out_128,
            "answers_hitting_cap": hits_cap_128,
            "truncated_answers": truncated_cnt_128,
        },
        "diagnostic_natural_256": {
            "output_stats": stats_out_diag,
            "answers_hitting_cap": hits_cap_diag,
            "truncated_answers": truncated_cnt_diag,
        },
        "input_stats": stats_in,
        "queries_prod": results_prod,
        "queries_diag": results_diag_natural,
    }

    with open("/tmp/real_production_output_benchmark.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 85)
    print("OUTPUT TOKEN BENCHMARK SUMMARY (30 REAL PRODUCTION RESPONSES)")
    print("=" * 85)
    print(f"PRODUCTION (num_predict=128):")
    print(f"  P50: {stats_out_128['p50']} | P90: {stats_out_128['p90']} | P95: {stats_out_128['p95']} | MAX: {stats_out_128['max']}")
    print(f"  Answers hitting cap (128): {hits_cap_128} | Truncated: {truncated_cnt_128}")
    print(f"\nNATURAL UNCONSTRAINED (diagnostic num_predict=256):")
    print(f"  P50: {stats_out_diag['p50']} | P90: {stats_out_diag['p90']} | P95: {stats_out_diag['p95']} | MAX: {stats_out_diag['max']}")
    print(f"  Answers hitting cap (256): {hits_cap_diag} | Truncated: {truncated_cnt_diag}")

if __name__ == "__main__":
    asyncio.run(main())
