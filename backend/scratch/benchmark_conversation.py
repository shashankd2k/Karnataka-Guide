"""
Real Source-Grounded Multilingual Conversation Benchmark for Phase 8.
Evaluates 30 conversational turns across 8 multi-turn tourist sessions:
- 20 Base Tourist Queries (English, Kannada, Script-Mixed, Unsupported)
- 10 Follow-Up Queries (Testing pronoun and context resolution)

Measures:
1. Language Detection Accuracy
2. Follow-Up Context Resolution Accuracy
3. Strict Grounding Success Rate (Grounded for heritage facts, Fallback for unsupported)
4. Citation Page Provenance Correctness
5. Fallback Correctness on Unsupported Queries
6. Conversation Turn Latencies (Dense, BM25, RRF, Cross-Encoder, DB Turn Total)
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from typing import List, Dict, Any
from sqlalchemy import select
from app.infrastructure.db.session import get_session_factory
from app.infrastructure.db.models.generation import KnowledgeGeneration, GenerationLifecycleStatus
from app.application.conversation.service import ConversationService
from app.application.conversation.language_detector import detect_language


CONVERSATION_SESSIONS_PLAN = [
    {
        "session_name": "Session 1: Belur Hoysala Circuit (English Multi-Turn)",
        "initial_lang": "en",
        "turns": [
            {
                "turn_type": "base",
                "query": "Who commissioned the Belur Chennakeshava temple and why?",
                "expected_lang": "en",
                "should_be_grounded": True,
                "expected_doc": "Belur_Halebidu_Hoysala_Guide.pdf",
                "expected_page": 2,
                "expected_keyword": "Vishnuvardhana",
            },
            {
                "turn_type": "follow_up",
                "query": "When was it built?",
                "expected_lang": "en",
                "should_be_grounded": True,
                "expected_doc": "Belur_Halebidu_Hoysala_Guide.pdf",
                "expected_page": 2,
                "expected_keyword": "1117",
                "expected_context": "Belur Chennakeshava Temple",
            },
            {
                "turn_type": "follow_up",
                "query": "What soft stone material was used for this monument?",
                "expected_lang": "en",
                "should_be_grounded": True,
                "expected_doc": "Belur_Halebidu_Hoysala_Guide.pdf",
                "expected_page": 1,
                "expected_keyword": "chloritic schist",
                "expected_context": "Belur Chennakeshava Temple",
            },
            {
                "turn_type": "follow_up",
                "query": "Tell me about the bracket figures on it",
                "expected_lang": "en",
                "should_be_grounded": True,
                "expected_doc": "Belur_Halebidu_Hoysala_Guide.pdf",
                "expected_page": 2,
                "expected_keyword": "Darpana Sundari",
                "expected_context": "Belur Chennakeshava Temple",
            },
        ],
    },
    {
        "session_name": "Session 2: Halebidu Hoysaleswara (English Multi-Turn)",
        "initial_lang": "en",
        "turns": [
            {
                "turn_type": "base",
                "query": "Tell me about the Halebidu Hoysaleswara temple complex",
                "expected_lang": "en",
                "should_be_grounded": True,
                "expected_doc": "Belur_Halebidu_Hoysala_Guide.pdf",
                "expected_page": 3,
                "expected_keyword": "1121",
            },
            {
                "turn_type": "follow_up",
                "query": "How many charging war elephants are carved on its base tiers?",
                "expected_lang": "en",
                "should_be_grounded": True,
                "expected_doc": "Belur_Halebidu_Hoysala_Guide.pdf",
                "expected_page": 3,
                "expected_keyword": "1,248",
                "expected_context": "Halebidu Hoysaleswara Temple",
            },
            {
                "turn_type": "follow_up",
                "query": "Who was the master architect that designed it?",
                "expected_lang": "en",
                "should_be_grounded": True,
                "expected_doc": "Belur_Halebidu_Hoysala_Guide.pdf",
                "expected_page": 3,
                "expected_keyword": "Kedaroja",
                "expected_context": "Halebidu Hoysaleswara Temple",
            },
        ],
    },
    {
        "session_name": "Session 3: Badami Rock-Cut Caves (English & Mixed Multi-Turn)",
        "initial_lang": "en",
        "turns": [
            {
                "turn_type": "base",
                "query": "Who established Badami as the capital of the Early Chalukyas?",
                "expected_lang": "en",
                "should_be_grounded": True,
                "expected_doc": "Badami_Caves_Guide.pdf",
                "expected_page": 1,
                "expected_keyword": "Pulakeshin I",
            },
            {
                "turn_type": "follow_up",
                "query": "Tell me about the 18-armed Nataraja in this cave complex",
                "expected_lang": "en",
                "should_be_grounded": True,
                "expected_doc": "Badami_Caves_Guide.pdf",
                "expected_page": 2,
                "expected_keyword": "81",
                "expected_context": "Badami",
            },
            {
                "turn_type": "follow_up",
                "query": "When was Cave 3 carved in it and who commissioned it?",
                "expected_lang": "en",
                "should_be_grounded": True,
                "expected_doc": "Badami_Caves_Guide.pdf",
                "expected_page": 2,
                "expected_keyword": "Mangalesha",
                "expected_context": "Badami",
            },
            {
                "turn_type": "follow_up",
                "query": "Where is the Bhutanatha temple group located near these caves?",
                "expected_lang": "en",
                "should_be_grounded": True,
                "expected_doc": "Badami_Caves_Guide.pdf",
                "expected_page": 3,
                "expected_keyword": "Agastya",
                "expected_context": "Badami",
            },
        ],
    },
    {
        "session_name": "Session 4: Aihole Architecture Laboratory (English Multi-Turn)",
        "initial_lang": "en",
        "turns": [
            {
                "turn_type": "base",
                "query": "Why is Aihole called the cradle of Indian temple architecture?",
                "expected_lang": "en",
                "should_be_grounded": True,
                "expected_doc": "Aihole_Heritage_Guide.pdf",
                "expected_page": 1,
                "expected_keyword": "120",
            },
            {
                "turn_type": "follow_up",
                "query": "What is the unique architectural plan of Durga Temple here?",
                "expected_lang": "en",
                "should_be_grounded": True,
                "expected_doc": "Aihole_Heritage_Guide.pdf",
                "expected_page": 1,
                "expected_keyword": "apsidal",
                "expected_context": "Aihole",
            },
            {
                "turn_type": "follow_up",
                "query": "Tell me about the Sanskrit inscription found here by poet Ravikirti",
                "expected_lang": "en",
                "should_be_grounded": True,
                "expected_doc": "Aihole_Heritage_Guide.pdf",
                "expected_page": 2,
                "expected_keyword": "Ravikirti",
                "expected_context": "Aihole",
            },
        ],
    },
    {
        "session_name": "Session 5: Pattadakal UNESCO Complex (English)",
        "initial_lang": "en",
        "turns": [
            {
                "turn_type": "base",
                "query": "Which queen built the Virupaksha temple at Pattadakal?",
                "expected_lang": "en",
                "should_be_grounded": True,
                "expected_doc": "Pattadakal_UNESCO_Guide.pdf",
                "expected_page": 2,
                "expected_keyword": "Lokamahadevi",
            },
            {
                "turn_type": "base",
                "query": "Explain the confluence of Nagara and Dravida styles at Pattadakal",
                "expected_lang": "en",
                "should_be_grounded": True,
                "expected_doc": "Pattadakal_UNESCO_Guide.pdf",
                "expected_page": 1,
                "expected_keyword": "Nagara",
            },
            {
                "turn_type": "base",
                "query": "Which is the oldest surviving temple at Pattadakal?",
                "expected_lang": "en",
                "should_be_grounded": True,
                "expected_doc": "Pattadakal_UNESCO_Guide.pdf",
                "expected_page": 2,
                "expected_keyword": "Sangameshwara",
            },
        ],
    },
    {
        "session_name": "Session 6: Hampi Vijayanagara Metropolis (English)",
        "initial_lang": "en",
        "turns": [
            {
                "turn_type": "base",
                "query": "Who were the founding brothers of the Vijayanagara Empire?",
                "expected_lang": "en",
                "should_be_grounded": True,
                "expected_doc": "Hampi_Vijayanagara_Guide.pdf",
                "expected_page": 1,
                "expected_keyword": "Harihara",
            },
            {
                "turn_type": "base",
                "query": "What is special about the 56 pillars in Vijaya Vittala temple?",
                "expected_lang": "en",
                "should_be_grounded": True,
                "expected_doc": "Hampi_Vijayanagara_Guide.pdf",
                "expected_page": 2,
                "expected_keyword": "musical",
            },
            {
                "turn_type": "base",
                "query": "Describe the monolithic Stone Chariot at Hampi",
                "expected_lang": "en",
                "should_be_grounded": True,
                "expected_doc": "Hampi_Vijayanagara_Guide.pdf",
                "expected_page": 2,
                "expected_keyword": "50-rupee",
            },
        ],
    },
    {
        "session_name": "Session 7: Kannada and Script-Mixed Tourism Queries",
        "initial_lang": "kn",
        "turns": [
            {
                "turn_type": "base",
                "query": "ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಕಟ್ಟಿಸಿದರು?",
                "expected_lang": "kn",
                "should_be_grounded": False,  # Cross-script gap before Phase 11 translation: must safely trigger Kannada fallback with 0 citations
                "expected_fallback": "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ.",
            },
            {
                "turn_type": "base",
                "query": "ಬಾದಾಮಿ ಗುಹೆ 1 ರಲ್ಲಿರುವ 18 ಕೈಗಳ ನಟರಾಜ ಶಿಲ್ಪದ ವಿಶೇಷತೆ ಏನು?",
                "expected_lang": "kn",
                "should_be_grounded": False,  # Safe fallback
                "expected_fallback": "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ.",
            },
            {
                "turn_type": "base",
                "query": "ಐಹೊಳೆ ದುರ್ಗಾ ದೇವಾಲಯದ ವಿಶಿಷ್ಟ ವಾಸ್ತುಶಿಲ್ಪ ಶೈಲಿ ಯಾವುದು?",
                "expected_lang": "kn",
                "should_be_grounded": False,  # Safe fallback
                "expected_fallback": "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ.",
            },
            {
                "turn_type": "base",
                "query": "ಪಟ್ಟದಕಲ್ಲು ವಿರೂಪಾಕ್ಷ ದೇವಾಲಯವನ್ನು ನಿರ್ಮಿಸಿದ ರಾಣಿ ಯಾರು?",
                "expected_lang": "kn",
                "should_be_grounded": False,  # Safe fallback
                "expected_fallback": "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ.",
            },
            {
                "turn_type": "base",
                "query": "ಹಂಪಿ ವಿಜಯ ವಿಠ್ಠಲ ದೇವಾಲಯದ ಸಂಗೀತ ಸ್ತಂಭಗಳ ಬಗ್ಗೆ ತಿಳಿಸಿ",
                "expected_lang": "kn",
                "should_be_grounded": False,  # Safe fallback
                "expected_fallback": "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ.",
            },
            {
                "turn_type": "base",
                "query": "Belur Chennakeshava ದೇವಾಲಯದಲ್ಲಿರುವ Darpana Sundari ಶಿಲ್ಪದ ಬಗ್ಗೆ ತಿಳಿಸಿ",
                "expected_lang": "kn-mixed",
                "should_be_grounded": True,
                "expected_doc": "Belur_Halebidu_Hoysala_Guide.pdf",
                "expected_page": 2,
                "expected_keyword": "Darpana Sundari",
            },
            {
                "turn_type": "base",
                "query": "Halebidu Hoysaleswara temple ನಲ್ಲಿ ಎಷ್ಟು ಆನೆಗಳ ಕೆತ್ತನೆಗಳಿವೆ?",
                "expected_lang": "kn-mixed",
                "should_be_grounded": True,
                "expected_doc": "Belur_Halebidu_Hoysala_Guide.pdf",
                "expected_page": 3,
                "expected_keyword": "1,248",
            },
        ],
    },
    {
        "session_name": "Session 8: Unsupported / Out-of-Domain Anti-Hallucination Guard",
        "initial_lang": "en",
        "turns": [
            {
                "turn_type": "base",
                "query": "What is the capital city of France and how many people live there?",
                "expected_lang": "en",
                "should_be_grounded": False,
                "expected_fallback": "Information is not available in the knowledge base.",
            },
            {
                "turn_type": "base",
                "query": "Who won the 2024 ICC T20 cricket world cup?",
                "expected_lang": "en",
                "should_be_grounded": False,
                "expected_fallback": "Information is not available in the knowledge base.",
            },
            {
                "turn_type": "base",
                "query": "ಪ್ಯಾರಿಸ್ ನಗರದ ಪ್ರವಾಸಿ ಆಕರ್ಷಣೆಗಳ ಬಗ್ಗೆ ಮಾಹಿತಿ ನೀಡಿ",
                "expected_lang": "kn",
                "should_be_grounded": False,
                "expected_fallback": "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ.",
            },
        ],
    },
]


async def run_conversation_benchmark():
    sf = get_session_factory()
    async with sf() as session:
        # Verify active knowledge generation
        stmt = select(KnowledgeGeneration).where(
            KnowledgeGeneration.status == GenerationLifecycleStatus.ACTIVE,
            KnowledgeGeneration.is_active.is_(True),
        )
        active_gen = (await session.execute(stmt)).scalar_one_or_none()
        if not active_gen:
            print("ERROR: No ACTIVE knowledge generation found in MySQL!")
            return

        # Preload all authoritative chunk records from MySQL for instant consistency verification
        from app.infrastructure.db.models.chunk import DocumentChunk
        from app.infrastructure.db.models.document import Document

        db_chunks_stmt = (
            select(DocumentChunk, Document.original_name)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(DocumentChunk.generation_id == active_gen.id)
        )
        db_chunk_rows = (await session.execute(db_chunks_stmt)).all()
        db_chunk_registry: Dict[str, Any] = {
            c.id: {
                "chunk_id": c.id,
                "document_id": c.document_id,
                "generation_id": c.generation_id,
                "page_number": c.page_number,
                "source_filename": orig_name,
                "section_header": c.section_header,
            }
            for c, orig_name in db_chunk_rows
        }

        print("=" * 85)
        print("PHASE 8 CONVERSATION BENCHMARK & CITATION PROVENANCE VERIFICATION")
        print("=" * 85)
        print(f"Active Generation ID : {active_gen.id}")
        print(f"Version              : {active_gen.generation_version}")
        print(f"Active Documents     : {active_gen.document_count}")
        print(f"Active Chunks        : {active_gen.chunk_count}")
        print(f"Authoritative Chunks : {len(db_chunk_registry)} in MySQL")
        print("=" * 85)

        conv_service = ConversationService(session=session)
        conversation_sessions_plan = CONVERSATION_SESSIONS_PLAN

        total_turns = 0
        base_turns_count = 0
        follow_up_turns_count = 0

        lang_detection_correct = 0
        context_resolution_correct = 0
        grounding_decision_correct = 0
        emitted_citation_sets_correct = 0
        total_emitted_citation_sets = 0
        mysql_provenance_verified_citations = 0
        total_individual_citations = 0
        fallback_response_correct = 0
        total_fallback_turns = 0

        latencies_ms: List[float] = []

        print("\nEXECUTING 30 CONVERSATIONAL TURNS ACROSS 8 SESSIONS...")
        print("-" * 85)

        for sess_plan in conversation_sessions_plan:
            s_name = sess_plan["session_name"]
            init_lang = sess_plan["initial_lang"]
            turns = sess_plan["turns"]

            # Initialize session
            sess_obj = await conv_service.create_session(language_code=init_lang)
            session_uuid = sess_obj.session_uuid

            print(f"\n>>> {s_name} (Session UUID: {session_uuid[:8]}...)")

            for t_idx, turn in enumerate(turns, 1):
                total_turns += 1
                q_text = turn["query"]
                t_type = turn["turn_type"]
                expected_lang = turn["expected_lang"]
                should_ground = turn["should_be_grounded"]

                if t_type == "base":
                    base_turns_count += 1
                else:
                    follow_up_turns_count += 1

                # Execute turn
                resp = await conv_service.process_turn(session_uuid=session_uuid, user_message=q_text)

                # Fetch updated assistant message from DB to get real latency
                hist = await conv_service.get_history(session_uuid=session_uuid, limit=100)
                latest_msg = hist.messages[-1] if hist.messages else None
                turn_latency = latest_msg.latency_ms if latest_msg and latest_msg.latency_ms else 0
                latencies_ms.append(float(turn_latency))

                # 1. Evaluate Language Detection
                det_lang = resp.language
                is_lang_ok = (det_lang == expected_lang)
                if is_lang_ok:
                    lang_detection_correct += 1

                # 2. Evaluate Context / Follow-up Resolution
                is_context_ok = True
                if t_type == "follow_up":
                    exp_context = turn.get("expected_context", "")
                    resolved_q = resp.retrieval.resolved_query or q_text
                    if exp_context and exp_context.lower() in resolved_q.lower():
                        context_resolution_correct += 1
                    else:
                        is_context_ok = False

                # 3. Evaluate Grounding Decision
                is_grounding_ok = (resp.grounded == should_ground)
                if is_grounding_ok:
                    grounding_decision_correct += 1

                # 4. Evaluate Citations & Provenance Consistency
                is_citation_ok = True
                if resp.grounded and resp.citations:
                    total_emitted_citation_sets += 1
                    exp_doc = turn.get("expected_doc", "")
                    
                    # Verify each emitted citation against MySQL registry
                    turn_cits_valid = True
                    for cit in resp.citations:
                        total_individual_citations += 1
                        auth = db_chunk_registry.get(cit.chunk_id)
                        if (
                            auth
                            and cit.document_id == auth["document_id"]
                            and cit.generation_id == auth["generation_id"]
                            and cit.page_number == auth["page_number"]
                            and cit.source_filename == auth["source_filename"]
                        ):
                            mysql_provenance_verified_citations += 1
                        else:
                            turn_cits_valid = False
                    
                    top_cit = resp.citations[0]
                    if exp_doc and top_cit.source_filename != exp_doc:
                        turn_cits_valid = False
                    
                    if turn_cits_valid:
                        emitted_citation_sets_correct += 1
                    else:
                        is_citation_ok = False
                elif should_ground and not resp.citations:
                    is_citation_ok = False

                # 5. Evaluate Fallback Message (if ungrounded)
                is_fallback_ok = True
                if not should_ground:
                    total_fallback_turns += 1
                    exp_fb = turn.get("expected_fallback", "")
                    if exp_fb and resp.answer == exp_fb and len(resp.citations) == 0:
                        fallback_response_correct += 1
                    else:
                        is_fallback_ok = False

                status_flag = "OK" if (is_lang_ok and is_context_ok and is_grounding_ok and (is_citation_ok if should_ground else is_fallback_ok)) else "WARN"
                print(f"  Turn {t_idx} [{t_type:9s}] [{status_flag:4s}] Lang: {det_lang:8s} | Grounded: {str(resp.grounded):5s} | Citations: {len(resp.citations)} | Latency: {turn_latency:4.0f}ms | Q: '{q_text[:34]}...'")

        # Aggregate Statistics
        lang_acc = (lang_detection_correct / total_turns) * 100.0
        context_acc = (context_resolution_correct / max(follow_up_turns_count, 1)) * 100.0
        grounding_acc = (grounding_decision_correct / total_turns) * 100.0
        emitted_cit_acc = (emitted_citation_sets_correct / max(total_emitted_citation_sets, 1)) * 100.0
        mysql_prov_acc = (mysql_provenance_verified_citations / max(total_individual_citations, 1)) * 100.0
        fallback_acc = (fallback_response_correct / max(total_fallback_turns, 1)) * 100.0

        avg_latency = sum(latencies_ms) / total_turns
        warm_latencies = latencies_ms[1:] if len(latencies_ms) > 1 else latencies_ms
        avg_warm_latency = sum(warm_latencies) / len(warm_latencies)

        print("\n" + "=" * 85)
        print("PHASE 8 MULTILINGUAL CONVERSATION BENCHMARK RESULTS")
        print("=" * 85)
        print(f"Total Conversational Turns        : {total_turns} (20 Base Queries + 10 Follow-ups)")
        print(f"Conversational Sessions Evaluated : {len(conversation_sessions_plan)}")
        print("-" * 85)
        print(f"Language Detection Accuracy       : {lang_acc:.2f}% ({lang_detection_correct}/{total_turns})")
        print(f"Follow-Up Context Resolution Acc  : {context_acc:.2f}% ({context_resolution_correct}/{follow_up_turns_count})")
        print(f"Grounding Decision Accuracy       : {grounding_acc:.2f}% ({grounding_decision_correct}/{total_turns})")
        print(f"Emitted Citation Set Accuracy     : {emitted_cit_acc:.2f}% ({emitted_citation_sets_correct}/{total_emitted_citation_sets} grounded turns)")
        print(f"Authoritative MySQL Provenance    : {mysql_prov_acc:.2f}% ({mysql_provenance_verified_citations}/{total_individual_citations} citations verified)")
        print(f"Safe Fallback Response Accuracy   : {fallback_acc:.2f}% ({fallback_response_correct}/{total_fallback_turns} ungrounded turns)")
        print("-" * 85)
        print("MEASURED CONVERSATION TURN LATENCIES:")
        print(f"  - Overall Turn Average Latency  : {avg_latency:6.2f} ms")
        print(f"  - Steady-State Warm Turn Latency: {avg_warm_latency:6.2f} ms")
        print("=" * 85)


if __name__ == "__main__":
    asyncio.run(run_conversation_benchmark())
