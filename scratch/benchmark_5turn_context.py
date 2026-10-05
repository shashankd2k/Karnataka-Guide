import asyncio
import json
import os
import sys
import uuid
import urllib.request
import urllib.error
import statistics
import time
from typing import Dict, List, Any

from app.infrastructure.db.session import get_session_factory
from app.infrastructure.db.models.chat import ChatSession, ChatMessage, SenderType
from app.application.conversation.language_detector import detect_language
from app.application.conversation.context_builder import resolve_follow_up_query
from app.application.rag.service import RAGRetrievalService
from app.application.rag.schemas import RetrievalDiagnosticRequest
from app.application.rag.prompt_builder import build_grounded_prompt
from app.application.conversation.grounding_guard import GroundingGuard
from app.application.conversation.citation_formatter import sanitize_model_citations
from app.application.translation.service import TranslationService
from app.core.config import get_settings
from sqlalchemy import select

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "host.docker.internal:11434")

CONVERSATION_CHAINS = [
    {
        "name": "Chain A: English Entity/Coreference Chain (Chennakeshava)",
        "turns": [
            "Tell me about Chennakeshava Temple.",
            "Who commissioned it?",
            "When was it built?",
            "What architectural style does it use?",
            "What is special about its sculptures?"
        ]
    },
    {
        "name": "Chain B: English Detailed Architecture Chain (Halebidu & Hoysala)",
        "turns": [
            "Tell me about the Hoysaleswara Temple at Halebidu.",
            "Why was it left incomplete?",
            "What are the friezes on the lower wall tiers?",
            "Are there Jain basadis nearby in Halebidu?",
            "How far is it from Belur and how can tourists travel between them?"
        ]
    },
    {
        "name": "Chain C: English Detailed Architecture Chain (Hampi Vijayanagara)",
        "turns": [
            "Describe the Vijayanagara ruins at Hampi.",
            "What is unique about the Vittala Temple complex?",
            "Describe the stone chariot inside the temple.",
            "Tell me about the musical pillars in the Ranga Mandapa.",
            "What are the visiting hours and entry fees for the monuments?"
        ]
    },
    {
        "name": "Chain D: Kannada Follow-Up Chain (Belur)",
        "turns": [
            "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ನಿರ್ಮಿಸಿದರು?",
            "ಅದನ್ನು ಯಾವಾಗ ನಿರ್ಮಿಸಲಾಯಿತು?",
            "ಅದರ ವಾಸ್ತುಶಿಲ್ಪ ಶೈಲಿ ಯಾವುದು?",
            "ಅಲ್ಲಿರುವ ಶಿಲಾಬಾಲಿಕೆಯರ ವಿಶೇಷತೆ ಏನು?",
            "ಅಲ್ಲಿಗೆ ಭೇಟಿ ನೀಡಲು ಸೂಕ್ತ ಸಮಯ ಯಾವುದು?"
        ]
    },
    {
        "name": "Chain E: Mixed English / Kannada Chain",
        "turns": [
            "Tell me about Chennakeshava Temple at Belur.",
            "ಅಲ್ಲಿ ಪ್ರವೇಶ ಶುಲ್ಕ ಎಷ್ಟು?",
            "Is photography allowed inside?",
            "ಹಳೆಬೀಡು ಇಲ್ಲಿಂದ ಎಷ್ಟು ದೂರ?",
            "Can you summarize the best travel itinerary for visiting both Belur and Halebidu?"
        ]
    },
    {
        "name": "Chain F: Badami & Pattadakal Architectural Chain",
        "turns": [
            "What are the rock-cut cave temples of Badami?",
            "Describe Cave 3 dedicated to Vishnu.",
            "What about the Chalukya temples at Pattadakal?",
            "Explain the difference between southern Dravida and northern Nagara styles there.",
            "Which is the largest temple in Pattadakal?"
        ]
    }
]

def query_ollama(system_prompt: str, user_prompt: str, num_predict: int = 64) -> Dict[str, Any]:
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
        "keep_alive": "30m",
        "options": options
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"http://{OLLAMA_HOST}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))

def count_tokens(text: str, is_system: bool = False) -> int:
    """Helper to get exact token count for sub-components using Ollama prompt_eval_count."""
    if not text.strip():
        return 0
    payload = {
        "model": "phi3:mini",
        "prompt": "" if is_system else text,
        "system": text if is_system else "",
        "stream": False,
        "keep_alive": "30m",
        "options": {"num_ctx": 1024, "num_predict": 1}
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"http://{OLLAMA_HOST}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            return res.get("prompt_eval_count", 0)
    except Exception:
        return len(text.split())

async def run_5turn_benchmark():
    settings = get_settings()
    factory = get_session_factory()
    grounding_guard = GroundingGuard(min_score_threshold=settings.CONVERSATION_GROUNDING_MIN_SCORE)
    translation_service = TranslationService()

    print("=" * 85)
    print("REAL 5-TURN CONTEXT BUDGET BENCHMARK (ACTUAL CONTEXT BUILDER & RETRIEVAL)")
    print(f"Ollama Target Host: {OLLAMA_HOST}")
    print("=" * 85)

    final_turn_input_tokens = []
    chain_results = []

    async with factory() as db_session:
        rag_service = RAGRetrievalService(session=db_session)

        for chain in CONVERSATION_CHAINS:
            chain_name = chain["name"]
            turns = chain["turns"]
            print(f"\n--- Running {chain_name} ---")

            # Create clean test chat session
            sess = ChatSession(
                id=str(uuid.uuid4()),
                session_uuid=str(uuid.uuid4()),
                language_code="en",
            )
            db_session.add(sess)
            await db_session.commit()
            await db_session.refresh(sess)

            turn_details = []

            for turn_idx, query_text in enumerate(turns, start=1):
                # 1. Fetch real bounded history from DB
                stmt_history = (
                    select(ChatMessage)
                    .where(ChatMessage.session_id == sess.id)
                    .order_by(ChatMessage.created_at.desc())
                    .limit(10)
                )
                history_desc = (await db_session.execute(stmt_history)).scalars().all()
                history_asc = list(reversed(history_desc))

                # 2. Context resolution via actual production context builder
                resolved_query = resolve_follow_up_query(query_text, history_asc)

                # 3. Detect language & translate if Kannada
                lang_res = detect_language(query_text)
                effective_lang = lang_res.language if lang_res.language in ("kn", "en") else "en"

                if effective_lang == "kn":
                    search_query = await translation_service.translate_retrieval_query(
                        resolved_query, from_lang="kn", to_lang="en"
                    )
                else:
                    search_query = resolved_query

                # 4. Phase 7 Hybrid Evidence Retrieval (BM25 + Dense + RRF + Cross-Encoder)
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

                # 5. Grounding evaluation
                grounding_res = grounding_guard.evaluate(
                    candidates=retrieval_resp.results,
                    language=effective_lang,
                    active_generation_id=retrieval_resp.active_generation_id,
                )

                if grounding_res.is_grounded and retrieval_resp.results:
                    sys_prompt, user_prompt, auth_labels = build_grounded_prompt(
                        query=search_query,
                        candidates=retrieval_resp.results,
                        language="en",
                        max_chars=settings.OLLAMA_MAX_CONTEXT_CHARS,
                    )
                    # For turns 1-4, generate 32 tokens; for turn 5 generate 64 tokens
                    predict_tokens = 64 if turn_idx == 5 else 32
                    res = query_ollama(sys_prompt, user_prompt, num_predict=predict_tokens)
                    prompt_eval_tokens = res.get("prompt_eval_count", 0)
                    eval_tokens = res.get("eval_count", 0)
                    answer_text = sanitize_model_citations(res.get("response", "").strip(), auth_labels)
                else:
                    sys_prompt = ""
                    user_prompt = ""
                    prompt_eval_tokens = 0
                    eval_tokens = 0
                    answer_text = "Information is not available in the knowledge base."

                # Detailed component breakdown on final (5th) turn
                comp_breakdown = {}
                if turn_idx == 5 and sys_prompt and user_prompt:
                    sys_tokens = count_tokens(sys_prompt, is_system=True)
                    parts = user_prompt.rsplit("\n\nTourist Question: ", 1)
                    evidence_part = parts[0] if len(parts) > 1 else user_prompt
                    query_part = ("Tourist Question: " + parts[1]) if len(parts) > 1 else ""
                    evidence_tokens = count_tokens(evidence_part, is_system=False)
                    query_tokens = count_tokens(query_part, is_system=False)
                    comp_breakdown = {
                        "system_policy_tokens": sys_tokens,
                        "evidence_tokens": evidence_tokens,
                        "query_tokens": query_tokens,
                        "history_resolution": f"'{query_text}' -> '{resolved_query}'",
                        "total_input_tokens": prompt_eval_tokens,
                    }

                # Save user & assistant messages to DB for subsequent turns
                user_msg = ChatMessage(
                    id=str(uuid.uuid4()),
                    session_id=sess.id,
                    sender_type=SenderType.USER,
                    message_text=query_text,
                )
                db_session.add(user_msg)
                await db_session.flush()

                asst_msg = ChatMessage(
                    id=str(uuid.uuid4()),
                    session_id=sess.id,
                    sender_type=SenderType.ASSISTANT,
                    message_text=answer_text,
                )
                db_session.add(asst_msg)
                await db_session.commit()

                turn_info = {
                    "turn": turn_idx,
                    "query": query_text,
                    "resolved_query": resolved_query,
                    "input_tokens": prompt_eval_tokens,
                    "output_tokens": eval_tokens,
                    "components": comp_breakdown,
                }
                turn_details.append(turn_info)
                print(f"  Turn {turn_idx}: '{query_text[:30]}...' -> Resolved: '{resolved_query[:30]}...' | In: {prompt_eval_tokens:3d} tok | Out: {eval_tokens:3d} tok")

                if turn_idx == 5:
                    final_turn_input_tokens.append(prompt_eval_tokens)

            chain_results.append({
                "chain_name": chain_name,
                "turns": turn_details,
                "final_turn_input_tokens": turn_details[-1]["input_tokens"],
                "final_turn_components": turn_details[-1]["components"],
            })

    # Statistical computation on 5th turn inputs
    s_tokens = sorted(final_turn_input_tokens)
    n = len(s_tokens)
    p50 = round(statistics.median(s_tokens), 1)
    p90 = round(s_tokens[int(0.90 * (n - 1))], 1)
    p95 = round(s_tokens[int(0.95 * (n - 1))], 1)
    max_val = max(s_tokens)

    budget_summary = {
        "final_turn_tokens": {
            "p50": p50,
            "p90": p90,
            "p95": p95,
            "max": max_val,
            "all_measured": final_turn_input_tokens,
        },
        "chains": chain_results,
    }

    out_path = "/tmp/real_5turn_context_budget.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(budget_summary, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 85)
    print("5-TURN INPUT TOKEN BENCHMARK SUMMARY (MEASURED)")
    print("=" * 85)
    print(f"5-TURN INPUT P50: {p50}")
    print(f"5-TURN INPUT P90: {p90}")
    print(f"5-TURN INPUT P95: {p95}")
    print(f"5-TURN INPUT MAX: {max_val}")
    print(f"All 5th-Turn Measurements: {final_turn_input_tokens}")
    for c in chain_results:
        print(f"\n  {c['chain_name']}: Final Turn Input = {c['final_turn_input_tokens']} tok")
        comps = c.get("final_turn_components", {})
        if comps:
            print(f"    Breakdown -> System: {comps.get('system_policy_tokens')} | Evidence: {comps.get('evidence_tokens')} | Query: {comps.get('query_tokens')}")

if __name__ == "__main__":
    asyncio.run(run_5turn_benchmark())
