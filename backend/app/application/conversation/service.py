"""
Conversation orchestrator service managing anonymous tourist sessions,
multi-turn context resolution, Phase 7 retrieval execution, strict grounding
guards, citation compilation, and MySQL persistence.
"""

import hashlib
import time
from typing import Any, AsyncIterator, Dict, List, Optional
import uuid
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
from app.core.config import get_settings
from app.core.errors import BadRequestException, NotFoundException
from app.infrastructure.db.models.chat import ChatMessage, ChatSession, SenderType
from app.application.conversation.language_detector import detect_language
from app.application.conversation.context_builder import resolve_follow_up_query
from app.application.conversation.grounding_guard import GroundingGuard
from app.application.conversation.citation_formatter import (
    extract_authoritative_citations,
    filter_authoritative_citations,
    format_citations_and_evidence,
    sanitize_model_citations,
)
from app.application.conversation.schemas import (
    ChatMessageItem,
    ChatTurnResponse,
    CitationItem,
    DeleteSessionResponse,
    RetrievalMeta,
    SessionHistoryResponse,
    SessionResponse,
)
from app.application.rag.service import RAGRetrievalService
from app.application.rag.schemas import RetrievalDiagnosticRequest
from app.application.rag.prompt_builder import build_grounded_prompt, select_grounded_candidates
from app.application.translation.service import TranslationService
from app.domain.ports.llm import ILLMProvider
from app.infrastructure.llm.ollama import OllamaLLMProvider, get_ollama_provider

logger = structlog.get_logger(__name__)


class ConversationService:
    """Orchestrates anonymous multilingual conversations for the tourist interface."""

    def __init__(
        self,
        session: AsyncSession,
        llm_provider: Optional[ILLMProvider] = None,
        translation_service: Optional[TranslationService] = None,
    ):
        self.session = session
        self.settings = get_settings()
        self.grounding_guard = GroundingGuard(
            min_score_threshold=self.settings.CONVERSATION_GROUNDING_MIN_SCORE
        )
        self.llm_provider = llm_provider or get_ollama_provider()
        self.translation_service = translation_service or TranslationService()

    async def create_session(
        self,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        language_code: str = "kn",
    ) -> SessionResponse:
        """
        Create a new anonymous, unauthenticated tourist chat session.
        """
        ip_hash = None
        if client_ip:
            ip_hash = hashlib.sha256(client_ip.encode("utf-8")).hexdigest()

        # Sanitize language code preference
        lang = language_code.strip().lower() if language_code else "kn"
        if lang not in ("kn", "en"):
            lang = "kn"

        chat_session = ChatSession(
            id=str(uuid.uuid4()),
            session_uuid=str(uuid.uuid4()),
            language_code=lang,
            client_ip_hash=ip_hash,
            user_agent=user_agent[:255] if user_agent else None,
        )

        self.session.add(chat_session)
        await self.session.commit()
        await self.session.refresh(chat_session)

        logger.info(
            "tourist_session_created",
            session_uuid=chat_session.session_uuid,
            language_code=chat_session.language_code,
        )

        return SessionResponse(
            session_uuid=chat_session.session_uuid,
            language_code=chat_session.language_code,
            created_at=chat_session.created_at,
        )

    async def get_session_by_uuid(self, session_uuid: str) -> ChatSession:
        """
        Fetch a chat session by its public UUID, or raise NotFoundException.
        """
        stmt = select(ChatSession).where(ChatSession.session_uuid == session_uuid)
        result = await self.session.execute(stmt)
        chat_session = result.scalar_one_or_none()

        if not chat_session:
            raise NotFoundException(f"Tourist chat session '{session_uuid}' was not found.")

        return chat_session

    async def process_turn(
        self,
        session_uuid: str,
        user_message: str,
    ) -> ChatTurnResponse:
        """
        Process a single conversational turn from an anonymous tourist with grounded LLM generation.

        Flow:
            1. Validate session
            2. Detect language (English, Kannada, Mixed)
            3. Fetch recent conversation turns (bounded context)
            4. Resolve follow-up / pronoun references into self-contained search query
            5. Execute Phase 7 hybrid retrieval
            6. Evaluate strict grounding guard (with exact bilingual fallback)
            7. If ungrounded -> return exact fallback immediately with 0 citations (NO LLM CALL)
            8. If grounded -> construct isolated prompt, generate via Ollama, validate citations
            9. Fall back gracefully to extractive evidence if Ollama is unavailable
            10. Persist USER and ASSISTANT messages in MySQL
            11. Return structured response contract
        """
        start_time = time.perf_counter()
        chat_session = await self.get_session_by_uuid(session_uuid)

        raw_query = user_message.strip()
        if not raw_query:
            raise BadRequestException("User message cannot be empty.")

        # 1. Detect language & determine effective conversation language
        lang_res = detect_language(raw_query)
        effective_lang = lang_res.language if lang_res.language in ("kn", "en") else (chat_session.language_code or "kn")

        # 2. Fetch recent conversation history (bounded to last N turns = 2*N messages)
        max_messages = self.settings.CONVERSATION_MAX_TURNS * 2
        stmt_history = (
            select(ChatMessage)
            .where(ChatMessage.session_id == chat_session.id)
            .order_by(ChatMessage.created_at.desc())
            .limit(max_messages)
        )
        recent_messages_desc = (await self.session.execute(stmt_history)).scalars().all()
        recent_messages_asc = list(reversed(recent_messages_desc))

        # 3. Resolve follow-up query context
        resolved_search_query = resolve_follow_up_query(
            current_query=raw_query,
            history_messages=recent_messages_asc,
        )

        # 3.5. Phase 11 Retrieval Query Translation (Kannada -> English)
        retrieval_search_query = await self.translation_service.translate_retrieval_query(
            query=resolved_search_query,
            from_lang=effective_lang,
            to_lang="en",
        )

        # 4. Phase 7 Hybrid Evidence Retrieval (BM25 + Dense + RRF + Cross-Encoder)
        rag_service = RAGRetrievalService(session=self.session)
        retrieval_req = RetrievalDiagnosticRequest(
            query=retrieval_search_query,
            top_k=self.settings.RETRIEVAL_FINAL_TOP_K,
            dense_top_k=self.settings.RETRIEVAL_DENSE_TOP_K,
            bm25_top_k=self.settings.RETRIEVAL_BM25_TOP_K,
            rerank_candidates=self.settings.RETRIEVAL_RERANK_CANDIDATES,
            enable_reranker=True,
            filter_noise=True,
            suppress_duplicates=True,
        )
        retrieval_resp = await rag_service.retrieve_evidence(retrieval_req)

        # 5. Strict Grounding Guard
        grounding_result = self.grounding_guard.evaluate(
            candidates=retrieval_resp.results,
            language=effective_lang,
            active_generation_id=retrieval_resp.active_generation_id,
        )

        # 6. Grounded Answer Generation & Citation Validation
        if not grounding_result.is_grounded or not retrieval_resp.results:
            # Rule 1: DO NOT CALL OLLAMA if ungrounded. Return exact fallback and 0 citations.
            exact_fallback = "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ." if effective_lang == "kn" else "Information is not available in the knowledge base."
            answer_text = grounding_result.fallback_message or exact_fallback
            citations_list = []
            generation_mode = "fallback_ungrounded"
        else:
            # Build isolated prompt with anti-injection boundaries
            sys_prompt, user_prompt, auth_labels = build_grounded_prompt(
                query=retrieval_search_query,
                candidates=retrieval_resp.results,
                language="en",
                max_chars=self.settings.OLLAMA_MAX_CONTEXT_CHARS,
            )

            # Authoritative citations strictly matching the evidence supplied to the prompt
            accepted_candidates = select_grounded_candidates(
                candidates=retrieval_resp.results,
                max_chars=self.settings.OLLAMA_MAX_CONTEXT_CHARS,
                max_passages=2,
            )
            citations_list = extract_authoritative_citations(
                candidates=accepted_candidates,
                active_generation_id=retrieval_resp.active_generation_id,
                max_passages=len(accepted_candidates),
            )

            try:
                raw_answer = await self.llm_provider.generate_text(
                    system_prompt=sys_prompt,
                    user_prompt=user_prompt,
                    temperature=self.settings.OLLAMA_TEMPERATURE,
                )

                # Validate output
                if not raw_answer or raw_answer.strip() in (
                    grounding_result.fallback_message,
                    "Information is not available in the knowledge base.",
                    "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ.",
                ):
                    exact_fallback = "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ." if effective_lang == "kn" else "Information is not available in the knowledge base."
                    answer_text = grounding_result.fallback_message or exact_fallback
                    citations_list = []
                    generation_mode = "ollama_refused_exact_fallback"
                else:
                    # Sanitize citation labels to ensure only authorized [1], [2] are referenced
                    english_grounded_answer = sanitize_model_citations(raw_answer, auth_labels)
                    
                    # Phase 11 Grounded Response Translation (English -> Kannada)
                    if effective_lang == "kn":
                        answer_text = await self.translation_service.translate_response(
                            response=english_grounded_answer,
                            from_lang="en",
                            to_lang="kn",
                        )
                    else:
                        answer_text = english_grounded_answer

                    generation_mode = "ollama_grounded"

            except Exception as exc:
                # Rule 4: Graceful degradation to verified Phase 8 extractive evidence
                logger.warning(
                    "ollama_generation_degraded_to_extractive",
                    error=str(exc),
                    session_uuid=session_uuid,
                )
                extractive_answer, citations_list = format_citations_and_evidence(
                    candidates=retrieval_resp.results,
                    grounding_result=grounding_result,
                    active_generation_id=retrieval_resp.active_generation_id,
                )
                if effective_lang == "kn":
                    answer_text = await self.translation_service.translate_response(
                        response=extractive_answer,
                        from_lang="en",
                        to_lang="kn",
                    )
                else:
                    answer_text = extractive_answer
                generation_mode = "degraded_extractive"

        turn_duration_ms = int((time.perf_counter() - start_time) * 1000)

        # 7. Persist USER message (Original text stored verbatim without replacement)
        user_msg = ChatMessage(
            id=str(uuid.uuid4()),
            session_id=chat_session.id,
            sender_type=SenderType.USER,
            message_text=raw_query,  # Stored verbatim
            detected_language=effective_lang,
            audio_url=None,
            latency_ms=None,
            citations_json=None,
        )
        self.session.add(user_msg)

        # Filter authoritative citations to only those actually referenced by label in visible answer
        public_citations = filter_authoritative_citations(answer_text, citations_list)

        # 8. Persist ASSISTANT message
        citations_payload = {"citations": public_citations} if public_citations else None
        assistant_msg = ChatMessage(
            id=str(uuid.uuid4()),
            session_id=chat_session.id,
            sender_type=SenderType.ASSISTANT,
            message_text=answer_text,
            detected_language=effective_lang,
            audio_url=None,
            latency_ms=turn_duration_ms,
            citations_json=citations_payload,
        )
        self.session.add(assistant_msg)

        await self.session.commit()
        await self.session.refresh(assistant_msg)

        logger.info(
            "tourist_chat_turn_completed",
            session_uuid=session_uuid,
            language=lang_res.language,
            grounded=grounding_result.is_grounded,
            generation_mode=generation_mode,
            evidence_count=grounding_result.evidence_count,
            duration_ms=turn_duration_ms,
        )

        # Map citation items
        citation_items = [
            CitationItem(
                citation_label=c["citation_label"],
                source_filename=c["source_filename"],
                page_number=c["page_number"],
                section_header=c.get("section_header"),
                chunk_id=c.get("chunk_id"),
                document_id=c.get("document_id"),
                generation_id=c.get("generation_id"),
                reranker_score=c.get("reranker_score"),
            )
            for c in public_citations
        ]

        return ChatTurnResponse(
            session_uuid=session_uuid,
            message_id=assistant_msg.id,
            answer=answer_text,
            language=lang_res.language,
            grounded=grounding_result.is_grounded,
            citations=citation_items,
            retrieval=RetrievalMeta(
                generation_id=retrieval_resp.active_generation_id,
                evidence_count=len(retrieval_resp.results),
                resolved_query=resolved_search_query if resolved_search_query != raw_query else None,
            ),
            created_at=assistant_msg.created_at,
        )

    async def get_history(
        self,
        session_uuid: str,
        limit: int = 50,
    ) -> SessionHistoryResponse:
        """
        Retrieve paginated conversation history for an active session.
        """
        chat_session = await self.get_session_by_uuid(session_uuid)

        safe_limit = min(max(1, limit), 100)
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == chat_session.id)
            .order_by(ChatMessage.created_at.asc())
            .limit(safe_limit)
        )
        messages = (await self.session.execute(stmt)).scalars().all()

        message_items: List[ChatMessageItem] = []
        for m in messages:
            citations_data = m.citations_json.get("citations") if m.citations_json else None
            message_items.append(
                ChatMessageItem(
                    id=m.id,
                    sender_type=m.sender_type.value,
                    message_text=m.message_text,
                    detected_language=m.detected_language,
                    citations=citations_data,
                    latency_ms=m.latency_ms,
                    created_at=m.created_at,
                )
            )

        return SessionHistoryResponse(
            session_uuid=chat_session.session_uuid,
            language_code=chat_session.language_code,
            total_messages=len(message_items),
            messages=message_items,
        )

    async def delete_history(self, session_uuid: str) -> DeleteSessionResponse:
        """
        Clear all messages for a tourist session for privacy protection.
        """
        chat_session = await self.get_session_by_uuid(session_uuid)

        delete_stmt = delete(ChatMessage).where(ChatMessage.session_id == chat_session.id)
        res = await self.session.execute(delete_stmt)
        await self.session.commit()

        deleted_count = res.rowcount or 0
        logger.info("tourist_session_history_cleared", session_uuid=session_uuid, deleted_count=deleted_count)

        return DeleteSessionResponse(
            session_uuid=session_uuid,
            deleted_messages_count=deleted_count,
            message="Conversation history cleared successfully.",
        )

    async def stream_turn(
        self,
        session_uuid: str,
        user_message: str,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Process a conversational turn and stream tokens via Server-Sent Events (SSE).

        Flow & Invariants:
            1. Validate session & user message.
            2. Detect language & resolve follow-up context.
            3. Execute Phase 7 hybrid retrieval.
            4. Execute GroundingGuard BEFORE any token is sent to the client.
            5. If UNGROUNDED:
                - Emit exact fallback tokens.
                - Emit empty citations.
                - Persist turn in MySQL.
                - Emit done event.
            6. If GROUNDED:
                - Extract authoritative citations from retrieval metadata.
                - Stream generated tokens in real-time from Ollama.
                - Emit authoritative citations event.
                - Persist complete turn in MySQL only upon successful stream.
                - Emit done event.
        """
        start_time = time.perf_counter()
        chat_session = await self.get_session_by_uuid(session_uuid)

        raw_query = user_message.strip()
        if not raw_query:
            raise BadRequestException("User message cannot be empty.")

        # 1. Detect language & effective language
        lang_res = detect_language(raw_query)
        effective_lang = lang_res.language if lang_res.language in ("kn", "en") else (chat_session.language_code or "kn")

        # 2. Fetch history
        max_messages = self.settings.CONVERSATION_MAX_TURNS * 2
        stmt_history = (
            select(ChatMessage)
            .where(ChatMessage.session_id == chat_session.id)
            .order_by(ChatMessage.created_at.desc())
            .limit(max_messages)
        )
        recent_messages_desc = (await self.session.execute(stmt_history)).scalars().all()
        recent_messages_asc = list(reversed(recent_messages_desc))

        # 3. Resolve follow-up query
        resolved_search_query = resolve_follow_up_query(
            current_query=raw_query,
            history_messages=recent_messages_asc,
        )

        # 3.5. Translate retrieval query for Phase 7 retrieval
        retrieval_search_query = await self.translation_service.translate_retrieval_query(
            query=resolved_search_query,
            from_lang=effective_lang,
            to_lang="en",
        )

        # 4. Phase 7 Hybrid Evidence Retrieval
        rag_service = RAGRetrievalService(session=self.session)
        retrieval_req = RetrievalDiagnosticRequest(
            query=retrieval_search_query,
            top_k=self.settings.RETRIEVAL_FINAL_TOP_K,
            dense_top_k=self.settings.RETRIEVAL_DENSE_TOP_K,
            bm25_top_k=self.settings.RETRIEVAL_BM25_TOP_K,
            rerank_candidates=self.settings.RETRIEVAL_RERANK_CANDIDATES,
            enable_reranker=True,
            filter_noise=True,
            suppress_duplicates=True,
        )
        retrieval_resp = await rag_service.retrieve_evidence(retrieval_req)

        # 5. Strict Grounding Guard BEFORE STREAMING
        grounding_result = self.grounding_guard.evaluate(
            candidates=retrieval_resp.results,
            language=effective_lang,
            active_generation_id=retrieval_resp.active_generation_id,
        )

        # Ungrounded Branch
        if not grounding_result.is_grounded or not retrieval_resp.results:
            exact_fallback = "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ." if effective_lang == "kn" else "Information is not available in the knowledge base."
            fallback_text = grounding_result.fallback_message or exact_fallback
            yield {"event": "token", "data": {"text": fallback_text}}
            yield {"event": "citations", "data": {"citations": []}}

            turn_duration_ms = int((time.perf_counter() - start_time) * 1000)

            # Persist USER message
            user_msg = ChatMessage(
                id=str(uuid.uuid4()),
                session_id=chat_session.id,
                sender_type=SenderType.USER,
                message_text=raw_query,
                detected_language=effective_lang,
                latency_ms=None,
                citations_json=None,
            )
            self.session.add(user_msg)

            # Persist ASSISTANT message
            assistant_msg = ChatMessage(
                id=str(uuid.uuid4()),
                session_id=chat_session.id,
                sender_type=SenderType.ASSISTANT,
                message_text=fallback_text,
                detected_language=effective_lang,
                latency_ms=turn_duration_ms,
                citations_json=None,
            )
            self.session.add(assistant_msg)
            await self.session.commit()
            await self.session.refresh(assistant_msg)

            yield {
                "event": "done",
                "data": {
                    "session_uuid": session_uuid,
                    "message_id": assistant_msg.id,
                    "grounded": False,
                    "language": effective_lang,
                    "duration_ms": turn_duration_ms,
                },
            }
            return

        # Grounded Branch
        sys_prompt, user_prompt, auth_labels = build_grounded_prompt(
            query=retrieval_search_query,
            candidates=retrieval_resp.results,
            language="en",
            max_chars=self.settings.OLLAMA_MAX_CONTEXT_CHARS,
        )

        accepted_candidates = select_grounded_candidates(
            candidates=retrieval_resp.results,
            max_chars=self.settings.OLLAMA_MAX_CONTEXT_CHARS,
            max_passages=2,
        )
        citations_list = extract_authoritative_citations(
            candidates=accepted_candidates,
            active_generation_id=retrieval_resp.active_generation_id,
            max_passages=len(accepted_candidates),
        )

        accumulated_tokens: List[str] = []
        try:
            async for token in self.llm_provider.generate_stream(
                system_prompt=sys_prompt,
                user_prompt=user_prompt,
                temperature=self.settings.OLLAMA_TEMPERATURE,
            ):
                accumulated_tokens.append(token)
                if effective_lang != "kn":
                    yield {"event": "token", "data": {"text": token}}

            raw_answer = "".join(accumulated_tokens).strip()
            if not raw_answer or raw_answer in (
                grounding_result.fallback_message,
                "Information is not available in the knowledge base.",
                "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ.",
            ):
                exact_fallback = "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ." if effective_lang == "kn" else "Information is not available in the knowledge base."
                final_answer = grounding_result.fallback_message or exact_fallback
                citations_to_persist = None
                emitted_citations = []
                if effective_lang == "kn":
                    yield {"event": "token", "data": {"text": final_answer}}
            else:
                english_grounded_answer = sanitize_model_citations(raw_answer, auth_labels)
                if effective_lang == "kn":
                    final_answer = await self.translation_service.translate_response(
                        response=english_grounded_answer,
                        from_lang="en",
                        to_lang="kn",
                    )
                    yield {"event": "token", "data": {"text": final_answer}}
                else:
                    final_answer = english_grounded_answer

                emitted_citations = filter_authoritative_citations(final_answer, citations_list)
                citations_to_persist = {"citations": emitted_citations} if emitted_citations else None

        except Exception as exc:
            req_id = structlog.contextvars.get_contextvars().get("request_id")
            err_data: Dict[str, Any] = {
                "code": "SERVICE_UNAVAILABLE",
                "message": "Response generation became unavailable.",
            }
            if req_id:
                err_data["request_id"] = req_id

            if accumulated_tokens:
                logger.error(
                    "ollama_streaming_failed_mid_stream",
                    error=str(exc),
                    session_uuid=session_uuid,
                )
                # Mid-stream failure: Emit terminal error event and terminate without done/citations/persistence
                yield {
                    "event": "error",
                    "data": err_data,
                }
                return

            logger.warning(
                "ollama_streaming_failed_degraded_to_extractive",
                error=str(exc),
                session_uuid=session_uuid,
            )
            try:
                extractive_answer, citations_list = format_citations_and_evidence(
                    candidates=retrieval_resp.results,
                    grounding_result=grounding_result,
                    active_generation_id=retrieval_resp.active_generation_id,
                )
                yield {"event": "token", "data": {"text": extractive_answer}}
                final_answer = extractive_answer
                emitted_citations = filter_authoritative_citations(final_answer, citations_list)
                citations_to_persist = {"citations": emitted_citations} if emitted_citations else None
            except Exception as fallback_exc:
                logger.error("extractive_fallback_failed", error=str(fallback_exc))
                yield {
                    "event": "error",
                    "data": err_data,
                }
                return

        # Emit authoritative citations event
        yield {"event": "citations", "data": {"citations": emitted_citations}}

        turn_duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Persist user & assistant message upon completed stream
        user_msg = ChatMessage(
            id=str(uuid.uuid4()),
            session_id=chat_session.id,
            sender_type=SenderType.USER,
            message_text=raw_query,
            detected_language=lang_res.language,
            latency_ms=None,
            citations_json=None,
        )
        self.session.add(user_msg)

        assistant_msg = ChatMessage(
            id=str(uuid.uuid4()),
            session_id=chat_session.id,
            sender_type=SenderType.ASSISTANT,
            message_text=final_answer,
            detected_language=lang_res.language,
            latency_ms=turn_duration_ms,
            citations_json=citations_to_persist,
        )
        self.session.add(assistant_msg)
        await self.session.commit()
        await self.session.refresh(assistant_msg)

        yield {
            "event": "done",
            "data": {
                "session_uuid": session_uuid,
                "message_id": assistant_msg.id,
                "grounded": grounding_result.is_grounded,
                "language": lang_res.language,
                "duration_ms": turn_duration_ms,
            },
        }

