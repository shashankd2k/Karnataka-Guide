"""
Public, unauthenticated tourist conversation and session API endpoints.
"""

import json
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.db.session import get_db_session
from app.application.conversation.service import ConversationService
from app.application.conversation.schemas import (
    ChatTurnRequest,
    ChatTurnResponse,
    CreateSessionRequest,
    DeleteSessionResponse,
    SessionHistoryResponse,
    SessionResponse,
)

router = APIRouter(prefix="/tourist", tags=["Public Tourist Chat"])


@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create anonymous tourist session",
    description="Initializes an anonymous session UUID for conversational state tracking with zero authentication.",
)
async def create_tourist_session(
    request: Request,
    payload: Optional[CreateSessionRequest] = None,
    db: AsyncSession = Depends(get_db_session),
) -> SessionResponse:
    """Create a new anonymous tourist chat session."""
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    lang_pref = payload.language_code if payload else "kn"

    service = ConversationService(session=db)
    return await service.create_session(
        client_ip=client_ip,
        user_agent=user_agent,
        language_code=lang_pref,
    )


@router.post(
    "/chat",
    response_model=ChatTurnResponse,
    status_code=status.HTTP_200_OK,
    summary="Send tourist chat message",
    description="Processes a tourist query with language detection, multi-turn context resolution, hybrid retrieval, strict grounding, and real citations.",
)
async def send_chat_message(
    payload: ChatTurnRequest,
    db: AsyncSession = Depends(get_db_session),
) -> ChatTurnResponse:
    """Process an unauthenticated tourist conversational turn."""
    service = ConversationService(session=db)
    return await service.process_turn(
        session_uuid=payload.session_uuid,
        user_message=payload.message,
    )


@router.post(
    "/chat/stream",
    status_code=status.HTTP_200_OK,
    summary="Stream tourist chat message (SSE)",
    description="Streams tourist answer tokens via Server-Sent Events (SSE) with strict grounding guard and authoritative citations.",
    responses={
        200: {
            "content": {"text/event-stream": {}},
            "description": "Server-Sent Events stream emitting 'token', 'citations', 'done', and optional 'error' events.",
        },
        400: {"description": "Invalid message or empty content."},
        404: {"description": "Tourist session not found."},
        422: {"description": "Request validation error."},
    },
)
async def stream_chat_message(
    payload: ChatTurnRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    """
    Stream a tourist conversational turn token-by-token using Server-Sent Events (SSE).
    
    Pre-stream validation:
        - Validates session exists in MySQL (returning HTTP 404 JSON error envelope on failure).
        - Validates request payload schema (returning HTTP 422 JSON error envelope on failure).
    
    Mid-stream protocol:
        - Evaluates GroundingGuard BEFORE token generation.
        - Streams progressive answer text via 'event: token' with payload {"text": "..."}.
        - Emits server-authoritative citations via 'event: citations' with payload {"citations": [...]}.
        - Persists completed message and emits completion metadata via 'event: done'.
        - Emits terminal 'event: error' and terminates immediately on unexpected mid-stream failure.
    """
    service = ConversationService(session=db)

    # 1. Pre-stream validation: Ensure session exists (raises NotFoundError -> HTTP 404 JSON envelope)
    await service.get_session_by_uuid(payload.session_uuid)

    req_id = getattr(request.state, "request_id", None) or structlog.contextvars.get_contextvars().get("request_id")

    async def sse_event_stream():
        try:
            async for event in service.stream_turn(
                session_uuid=payload.session_uuid,
                user_message=payload.message,
            ):
                event_name = event.get("event", "message")
                event_data = json.dumps(event.get("data", {}), ensure_ascii=False)
                yield f"event: {event_name}\ndata: {event_data}\n\n"
        except Exception as exc:
            err_payload = {
                "code": "SERVICE_UNAVAILABLE",
                "message": "Response generation became unavailable.",
            }
            if req_id:
                err_payload["request_id"] = req_id
            err_data = json.dumps(err_payload, ensure_ascii=False)
            yield f"event: error\ndata: {err_data}\n\n"

    return StreamingResponse(
        sse_event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/sessions/{uuid}",
    response_model=SessionHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get tourist session history",
    description="Retrieves chronological message history for a given anonymous session UUID.",
)
async def get_session_history(
    uuid: str,
    limit: int = Query(default=50, ge=1, le=100, description="Max messages to retrieve"),
    db: AsyncSession = Depends(get_db_session),
) -> SessionHistoryResponse:
    """Retrieve message history for an anonymous tourist session."""
    service = ConversationService(session=db)
    return await service.get_history(session_uuid=uuid, limit=limit)


@router.delete(
    "/sessions/{uuid}",
    response_model=DeleteSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Clear tourist session history",
    description="Deletes all conversation messages for a session to preserve user privacy.",
)
async def delete_session_history(
    uuid: str,
    db: AsyncSession = Depends(get_db_session),
) -> DeleteSessionResponse:
    """Clear conversation history for an anonymous tourist session."""
    service = ConversationService(session=db)
    return await service.delete_history(session_uuid=uuid)
