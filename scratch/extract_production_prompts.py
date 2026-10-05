import asyncio
import json
from app.infrastructure.db.session import get_session_factory
from app.infrastructure.db.models.generation import KnowledgeGeneration
from app.application.conversation.language_detector import detect_language
from app.application.conversation.grounding_guard import GroundingGuard
from app.application.rag.service import RAGRetrievalService
from app.application.rag.schemas import RetrievalDiagnosticRequest
from app.application.rag.prompt_builder import build_grounded_prompt
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

async def main():
    settings = get_settings()
    factory = get_session_factory()
    grounding_guard = GroundingGuard(min_score_threshold=settings.CONVERSATION_GROUNDING_MIN_SCORE)
    translation_service = TranslationService()

    built_prompts = []
    print("Extracting production grounded prompts for 30 queries...", flush=True)

    async with factory() as db_session:
        # Verify active generation
        gen_stmt = select(KnowledgeGeneration).where(KnowledgeGeneration.is_active == True)
        gen = (await db_session.execute(gen_stmt)).scalar_one_or_none()
        print(f"Active Gen: {gen.id} ({gen.generation_version})", flush=True)

        rag_service = RAGRetrievalService(session=db_session)

        for item in PROMPTS:
            qid = item["id"]
            raw_query = item["query"]
            lang_res = detect_language(raw_query)
            effective_lang = lang_res.language if lang_res.language in ("kn", "en") else "en"

            if effective_lang == "kn":
                search_query = await translation_service.translate_retrieval_query(raw_query, from_lang="kn", to_lang="en")
            else:
                search_query = raw_query
            search_query = search_query[:500].strip()

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

            grounding_result = grounding_guard.evaluate(
                candidates=retrieval_resp.results,
                language=effective_lang,
                active_generation_id=retrieval_resp.active_generation_id,
            )

            is_grounded = grounding_result.is_grounded and bool(retrieval_resp.results)
            if is_grounded:
                sys_prompt, user_prompt, auth_labels = build_grounded_prompt(
                    query=search_query,
                    candidates=retrieval_resp.results,
                    language="en",
                    max_chars=settings.OLLAMA_MAX_CONTEXT_CHARS,
                )
                entry = {
                    "id": qid,
                    "query": raw_query,
                    "search_query": search_query,
                    "language": effective_lang,
                    "is_grounded": True,
                    "system_prompt": sys_prompt,
                    "user_prompt": user_prompt,
                    "auth_labels": auth_labels,
                    "fallback": None,
                    "prompt_chars": len(sys_prompt) + len(user_prompt),
                }
            else:
                exact_fallback = "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ." if effective_lang == "kn" else "Information is not available in the knowledge base."
                entry = {
                    "id": qid,
                    "query": raw_query,
                    "search_query": search_query,
                    "language": effective_lang,
                    "is_grounded": False,
                    "system_prompt": "",
                    "user_prompt": "",
                    "auth_labels": [],
                    "fallback": exact_fallback,
                    "prompt_chars": 0,
                }
            built_prompts.append(entry)
            print(f"[{qid}] Grounded: {is_grounded} | Chars: {entry['prompt_chars']}", flush=True)

    with open("/tmp/production_prompts_30.json", "w", encoding="utf-8") as f:
        json.dump(built_prompts, f, indent=2, ensure_ascii=False)
    print("Saved /tmp/production_prompts_30.json successfully!", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
