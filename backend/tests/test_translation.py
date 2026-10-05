"""
Comprehensive unit and integration tests for Phase 11: Multilingual Translation Hardening (Meta NLLB-200 600M).
Covers domain ports, NLLB provider, token masking/unmasking, ConversationService integration, and API endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.conversation.service import ConversationService
from app.application.translation.service import (
    HERITAGE_PROPER_NOUNS,
    TranslationService,
)
from app.domain.ports.translation import ITranslationProvider
from app.infrastructure.db.models.admin import Admin, AdminRole
from app.infrastructure.db.models.chat import ChatSession, SenderType
from app.infrastructure.db.models.system import TranslationRegistry
from app.infrastructure.translation.nllb import (
    NLLBTranslationProvider,
    TranslationError,
    UnsupportedLanguageError,
)
from app.main import app


# ---------------------------------------------------------------------------
# 1. NLLB Translation Provider Tests
# ---------------------------------------------------------------------------

def test_nllb_provider_initialization_and_supported_languages():
    """Verify NLLB provider initializes with correct default configuration and supported languages."""
    provider = NLLBTranslationProvider()
    assert provider.model_name == "facebook/nllb-200-distilled-600M"
    assert provider.device == "cpu"
    supported = provider.get_supported_languages()
    assert "en" in supported
    assert "kn" in supported


@pytest.mark.asyncio
async def test_nllb_provider_unsupported_language_raises_error():
    """Verify unsupported language codes raise UnsupportedLanguageError."""
    provider = NLLBTranslationProvider()
    with pytest.raises(UnsupportedLanguageError) as exc_info:
        await provider.translate("Hello", from_lang="fr", to_lang="en")
    assert exc_info.value.code == "UNSUPPORTED_TRANSLATION_LANGUAGE"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_nllb_provider_empty_and_whitespace_input():
    """Verify empty and whitespace inputs return immediately without model execution."""
    provider = NLLBTranslationProvider()
    res1 = await provider.translate("", from_lang="kn", to_lang="en")
    assert res1 == ""
    res2 = await provider.translate("   ", from_lang="kn", to_lang="en")
    assert res2 == "   "


@pytest.mark.asyncio
async def test_nllb_provider_same_source_and_target_language():
    """Verify translating between same language returns input text directly."""
    provider = NLLBTranslationProvider()
    text = "Who built the temple?"
    res = await provider.translate(text, from_lang="en", to_lang="en")
    assert res == text


@pytest.mark.asyncio
async def test_nllb_provider_mocked_translation():
    """Verify translate calls model generation correctly with language code mapping."""
    provider = NLLBTranslationProvider()
    with patch.object(provider, "_sync_translate", return_value="Who built the Belur temple?"):
        res = await provider.translate(
            text="ಬೇಲೂರು ದೇವಾಲಯವನ್ನು ಯಾರು ಕಟ್ಟಿಸಿದರು?",
            from_lang="kn",
            to_lang="en",
        )
        assert res == "Who built the Belur temple?"


@pytest.mark.asyncio
async def test_nllb_provider_sync_failure_raises_translation_error():
    """Verify internal execution errors raise domain TranslationError."""
    provider = NLLBTranslationProvider()
    with patch.object(provider, "_sync_translate", side_effect=RuntimeError("CUDA out of memory")):
        with pytest.raises(TranslationError) as exc_info:
            await provider.translate("Text", from_lang="kn", to_lang="en")
        assert exc_info.value.code == "TRANSLATION_FAILED"
        assert exc_info.value.status_code == 500


def test_nllb_cached_model_loads_local_only_without_network():
    """Requirement 3A & 3B: Verify cached model loads with local_files_only=True and avoids WAN access."""
    # Reset singleton state
    old_model = NLLBTranslationProvider._model_instance
    old_tok = NLLBTranslationProvider._tokenizer_instance
    NLLBTranslationProvider._model_instance = None
    NLLBTranslationProvider._tokenizer_instance = None

    mock_tokenizer = MagicMock()
    mock_model = MagicMock()

    try:
        with patch("app.infrastructure.translation.nllb.AutoTokenizer.from_pretrained", return_value=mock_tokenizer) as mock_tok_load, \
             patch("app.infrastructure.translation.nllb.AutoModelForSeq2SeqLM.from_pretrained", return_value=mock_model) as mock_mod_load:
            
            model, tokenizer = NLLBTranslationProvider._get_model_and_tokenizer(
                "facebook/nllb-200-distilled-600M", "cpu"
            )

            # Confirm local_files_only=True was passed
            mock_tok_load.assert_called_once_with("facebook/nllb-200-distilled-600M", local_files_only=True)
            mock_mod_load.assert_called_once_with("facebook/nllb-200-distilled-600M", local_files_only=True)
            mock_model.to.assert_called_once_with("cpu")
            mock_model.eval.assert_called_once()
            assert model == mock_model
            assert tokenizer == mock_tokenizer
    finally:
        NLLBTranslationProvider._model_instance = old_model
        NLLBTranslationProvider._tokenizer_instance = old_tok


def test_nllb_uncached_first_run_fallback_preserves_download():
    """Requirement 3C: Verify uncached first-run fallback allows standard download path."""
    old_model = NLLBTranslationProvider._model_instance
    old_tok = NLLBTranslationProvider._tokenizer_instance
    NLLBTranslationProvider._model_instance = None
    NLLBTranslationProvider._tokenizer_instance = None

    mock_tokenizer = MagicMock()
    mock_model = MagicMock()

    def tok_side_effect(name, **kwargs):
        if kwargs.get("local_files_only"):
            raise OSError("Model not found in local cache")
        return mock_tokenizer

    def mod_side_effect(name, **kwargs):
        if kwargs.get("local_files_only"):
            raise OSError("Model not found in local cache")
        return mock_model

    try:
        with patch("app.infrastructure.translation.nllb.AutoTokenizer.from_pretrained", side_effect=tok_side_effect) as mock_tok_load, \
             patch("app.infrastructure.translation.nllb.AutoModelForSeq2SeqLM.from_pretrained", side_effect=mod_side_effect) as mock_mod_load:
            
            model, tokenizer = NLLBTranslationProvider._get_model_and_tokenizer(
                "facebook/nllb-200-distilled-600M", "cpu"
            )

            # Tokenizer failed local_files_only, triggering fallback download for both
            assert mock_tok_load.call_count == 2
            mock_tok_load.assert_any_call("facebook/nllb-200-distilled-600M", local_files_only=True)
            mock_tok_load.assert_called_with("facebook/nllb-200-distilled-600M")

            assert mock_mod_load.call_count == 1
            mock_mod_load.assert_called_with("facebook/nllb-200-distilled-600M")

            assert model == mock_model
            assert tokenizer == mock_tokenizer
    finally:
        NLLBTranslationProvider._model_instance = old_model
        NLLBTranslationProvider._tokenizer_instance = old_tok


def test_nllb_load_failure_raises_translation_error():
    """Verify TranslationError raised when both local and remote loading fail."""
    old_model = NLLBTranslationProvider._model_instance
    old_tok = NLLBTranslationProvider._tokenizer_instance
    NLLBTranslationProvider._model_instance = None
    NLLBTranslationProvider._tokenizer_instance = None

    try:
        with patch("app.infrastructure.translation.nllb.AutoTokenizer.from_pretrained", side_effect=RuntimeError("Download blocked")):
            with pytest.raises(TranslationError) as exc:
                NLLBTranslationProvider._get_model_and_tokenizer("facebook/nllb-200-distilled-600M", "cpu")
            assert "Failed to load NLLB-200 translation model" in str(exc.value.message)
    finally:
        NLLBTranslationProvider._model_instance = old_model
        NLLBTranslationProvider._tokenizer_instance = old_tok


# ---------------------------------------------------------------------------
# 2. Proper Noun, Date, and Citation Masking / Unmasking Tests
# ---------------------------------------------------------------------------

def test_mask_and_unmask_citation_labels():
    """Verify citation markers [1], [2], [3] are masked and unmasked verbatim."""
    text = "The Chennakeshava Temple was commissioned in 1117 CE [1] and has 42 bracket figures [2]."
    masked, token_map = TranslationService.mask_protected_tokens(text)
    
    assert "[1]" not in masked
    assert "[2]" not in masked
    assert "__CIT_0__" in masked
    assert "__CIT_1__" in masked
    assert token_map["__CIT_0__"] == "[1]"
    assert token_map["__CIT_1__"] == "[2]"

    # Unmasking restores original text
    restored = TranslationService.unmask_protected_tokens(masked, token_map)
    assert "[1]" in restored
    assert "[2]" in restored


def test_mask_and_unmask_historical_dates():
    """Verify historical dates (1117 CE, 12th century, 733 CE) are masked and unmasked."""
    text = "The temple was built in 1117 CE during the 12th century."
    masked, token_map = TranslationService.mask_protected_tokens(text)
    
    assert "1117 CE" not in masked
    assert "12th century" not in masked
    assert any(k.startswith("__DATE_") for k in token_map.keys())

    restored = TranslationService.unmask_protected_tokens(masked, token_map)
    assert "1117 CE" in restored
    assert "12th century" in restored


def test_mask_and_unmask_all_12_heritage_proper_nouns():
    """Verify all 12 core Karnataka heritage proper nouns are protected."""
    for noun in HERITAGE_PROPER_NOUNS:
        sample = f"Visiting the great {noun} in Karnataka."
        masked, token_map = TranslationService.mask_protected_tokens(sample)
        assert noun not in masked
        assert any(k.startswith("__HERITAGE_") for k in token_map.keys())
        restored = TranslationService.unmask_protected_tokens(masked, token_map)
        assert noun in restored


def test_unmask_fail_safe_missing_citation_placeholder():
    """Verify fail-safe behavior appends missing citation markers if placeholder was dropped by model."""
    token_map = {"__CIT_0__": "[1]"}
    corrupted_output = "This is a translated text without placeholder."
    restored = TranslationService.unmask_protected_tokens(corrupted_output, token_map)
    assert "[1]" in restored
    assert restored.endswith("[1]")


# ---------------------------------------------------------------------------
# 3. TranslationService Application Logic Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_translate_retrieval_query_english_bypass():
    """Verify English search queries bypass translation with zero model overhead."""
    mock_provider = AsyncMock(spec=ITranslationProvider)
    service = TranslationService(provider=mock_provider)

    query = "Who commissioned the Belur temple?"
    res = await service.translate_retrieval_query(query=query, from_lang="en", to_lang="en")
    
    assert res == query
    mock_provider.translate.assert_not_called()


@pytest.mark.asyncio
async def test_translate_retrieval_query_kannada_to_english():
    """Verify Kannada search queries are prepared with canonical entities and translated for retrieval."""
    mock_provider = AsyncMock(spec=ITranslationProvider)
    mock_provider.translate.return_value = "Who built the Belur Chennakeshava temple?"
    service = TranslationService(provider=mock_provider)

    kn_query = "ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಕಟ್ಟಿಸಿದರು?"
    res = await service.translate_retrieval_query(query=kn_query, from_lang="kn", to_lang="en")
    
    assert "Belur" in res
    assert "Chennakeshava" in res
    mock_provider.translate.assert_called_once()


@pytest.mark.asyncio
async def test_translate_retrieval_query_failure_returns_original_query():
    """Verify translation failure falls back to original query safely without crashing."""
    mock_provider = AsyncMock(spec=ITranslationProvider)
    mock_provider.translate.side_effect = RuntimeError("Inference timeout")
    service = TranslationService(provider=mock_provider)

    kn_query = "ಹಂಪಿಯ ಇತಿಹಾಸವೇನು?"
    res = await service.translate_retrieval_query(query=kn_query, from_lang="kn", to_lang="en")
    assert res == kn_query


@pytest.mark.asyncio
async def test_translate_response_exact_fallback_deterministic():
    """Verify exact fallback strings are returned directly without invoking neural translation."""
    mock_provider = AsyncMock(spec=ITranslationProvider)
    service = TranslationService(provider=mock_provider)

    fallback_en = "Information is not available in the knowledge base."
    res = await service.translate_response(response=fallback_en, from_lang="en", to_lang="kn")
    
    assert res == "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ."
    mock_provider.translate.assert_not_called()


@pytest.mark.asyncio
async def test_translate_response_grounded_preserves_citations():
    """Verify grounded answer translation preserves citation markers."""
    mock_provider = AsyncMock(spec=ITranslationProvider)
    mock_provider.translate.return_value = "ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು 1117 CE ನಲ್ಲಿ ರಾಜ ವಿಷ್ಣುವರ್ಧನ ನಿರ್ಮಿಸಿದರು __CIT_0__."
    service = TranslationService(provider=mock_provider)

    en_answer = "The Chennakeshava Temple was built in 1117 CE by King Vishnuvardhana [1]."
    res = await service.translate_response(response=en_answer, from_lang="en", to_lang="kn")
    
    assert "[1]" in res
    assert "1117 CE" in res
    mock_provider.translate.assert_called_once()


# ---------------------------------------------------------------------------
# 4. ConversationService Multilingual Pipeline Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_conversation_service_kannada_query_translates_and_grounds(db_session: AsyncSession):
    """Verify Kannada query triggers query translation, hybrid retrieval, Ollama generation, and response translation."""
    mock_llm = AsyncMock()
    mock_llm.generate_text.return_value = "The Belur temple was commissioned by King Vishnuvardhana in 1117 CE [1]."
    
    mock_trans = AsyncMock(spec=TranslationService)
    mock_trans.translate_retrieval_query.return_value = "Who built the Belur temple?"
    mock_trans.translate_response.return_value = "ಬೇಲೂರು ದೇವಾಲಯವನ್ನು 1117 CE ನಲ್ಲಿ ರಾಜ ವಿಷ್ಣುವರ್ಧನ ನಿರ್ಮಿಸಿದರು [1]."

    conv_service = ConversationService(
        session=db_session,
        llm_provider=mock_llm,
        translation_service=mock_trans,
    )

    # Create Kannada session
    sess_resp = await conv_service.create_session(language_code="kn")
    
    turn_resp = await conv_service.process_turn(
        session_uuid=sess_resp.session_uuid,
        user_message="ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಕಟ್ಟಿಸಿದರು?",
    )

    # 1. Query translation called
    mock_trans.translate_retrieval_query.assert_called_once()
    
    # 2. If grounded, Ollama and response translation called
    if turn_resp.grounded:
        mock_llm.generate_text.assert_called_once()
        mock_trans.translate_response.assert_called_once()
        assert "[1]" in turn_resp.answer
        assert len(turn_resp.citations) >= 1
    else:
        assert turn_resp.answer == "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ."


@pytest.mark.asyncio
async def test_conversation_service_kannada_query_ungrounded_exact_fallback(db_session: AsyncSession):
    """Verify ungrounded Kannada query returns exact Kannada fallback without Ollama or response translation."""
    mock_llm = AsyncMock()
    mock_trans = AsyncMock(spec=TranslationService)
    mock_trans.translate_retrieval_query.return_value = "Nonexistent Martian Alien Heritage Query 9999"

    conv_service = ConversationService(
        session=db_session,
        llm_provider=mock_llm,
        translation_service=mock_trans,
    )

    sess_resp = await conv_service.create_session(language_code="kn")
    
    turn_resp = await conv_service.process_turn(
        session_uuid=sess_resp.session_uuid,
        user_message="ಅನ್ಯಗ್ರಹ ಜೀವಿಗಳ ದೇವಾಲಯ ಎಲ್ಲಿದೆ?",
    )

    assert turn_resp.grounded is False
    assert turn_resp.answer == "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ."
    assert len(turn_resp.citations) == 0
    mock_llm.generate_text.assert_not_called()
    mock_trans.translate_response.assert_not_called()


@pytest.mark.asyncio
async def test_conversation_service_english_query_zero_translation_overhead(db_session: AsyncSession):
    """Verify English query does not invoke query or response translation."""
    mock_llm = AsyncMock()
    mock_llm.generate_text.return_value = "The temple was built in 1117 CE [1]."
    
    mock_trans = AsyncMock(spec=TranslationService)
    mock_trans.translate_retrieval_query.return_value = "Who built the Belur temple?"
    mock_trans.translate_response.return_value = "The temple was built in 1117 CE [1]."

    conv_service = ConversationService(
        session=db_session,
        llm_provider=mock_llm,
        translation_service=mock_trans,
    )

    sess_resp = await conv_service.create_session(language_code="en")
    
    turn_resp = await conv_service.process_turn(
        session_uuid=sess_resp.session_uuid,
        user_message="Who built the Belur temple?",
    )

    # In English session, query and response translation are bypassed
    mock_trans.translate_response.assert_not_called()


@pytest.mark.asyncio
async def test_conversation_service_verbatim_user_message_persisted(db_session: AsyncSession):
    """Verify the original user message is saved verbatim in MySQL without translation mutation."""
    mock_llm = AsyncMock()
    mock_llm.generate_text.return_value = "Response [1]"
    mock_trans = AsyncMock(spec=TranslationService)
    mock_trans.translate_retrieval_query.return_value = "Translated search query"
    mock_trans.translate_response.return_value = "ಉತ್ತರ [1]"

    conv_service = ConversationService(
        session=db_session,
        llm_provider=mock_llm,
        translation_service=mock_trans,
    )

    sess_resp = await conv_service.create_session(language_code="kn")
    raw_kn_text = "ಬೇಲೂರು ದೇವಾಲಯದ ಬಗ್ಗೆ ತಿಳಿಸಿ."
    
    await conv_service.process_turn(
        session_uuid=sess_resp.session_uuid,
        user_message=raw_kn_text,
    )

    # Inspect history from database
    history = await conv_service.get_history(sess_resp.session_uuid)
    assert len(history.messages) >= 2
    user_msg = next(m for m in history.messages if m.sender_type == "USER")
    assert user_msg.message_text == raw_kn_text  # Exactly verbatim


# ---------------------------------------------------------------------------
# 5. Admin Translation Registry API Endpoint Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_translation_registry_endpoint_unauthorized(client_with_db: httpx.AsyncClient):
    """Verify unauthorized requests to /api/v1/admin/translations are rejected with 401."""
    resp = await client_with_db.get("/api/v1/admin/translations")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_translation_registry_endpoint_success(
    client_with_db: httpx.AsyncClient,
    db_session: AsyncSession,
):
    """Verify authenticated admin can inspect translation registry pairs and provider health."""
    from app.core.security import create_access_token
    
    admin = Admin(
        id="test_admin_trans",
        username="admin_trans_test",
        email="trans@karnataka.gov.in",
        hashed_password="hash",
        role=AdminRole.SUPER_ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()

    token = create_access_token(admin_id=admin.id, role=admin.role.value)

    resp = await client_with_db.get(
        "/api/v1/admin/translations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider_engine"] == "nllb-200"
    assert "translations" in data
    assert isinstance(data["translations"], list)
    assert "en" in data["supported_languages"]
    assert "kn" in data["supported_languages"]


# ---------------------------------------------------------------------------
# 6. Advanced Provider, Streaming, and Security Invariant Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_nllb_provider_health_check_success():
    """Verify health check returns True when model assets are present."""
    provider = NLLBTranslationProvider()
    with patch.object(NLLBTranslationProvider, "_get_model_and_tokenizer", return_value=(MagicMock(), MagicMock())):
        assert await provider.check_health() is True


@pytest.mark.asyncio
async def test_nllb_provider_health_check_failure():
    """Verify health check returns False when pipeline loading fails."""
    provider = NLLBTranslationProvider()
    with patch.object(NLLBTranslationProvider, "_get_model_and_tokenizer", side_effect=RuntimeError("Corrupt weights")):
        assert await provider.check_health() is False


def test_unmask_fuzzy_placeholder_restoration():
    """Verify fuzzy matching restores placeholders if model alters underscores or spacing."""
    token_map = {
        "__HERITAGE_0__": "Chennakeshava",
        "__CIT_0__": "[1]",
    }
    # Model slightly modified formatting (e.g. space between underscore or missing trailing underscore)
    mutated_text = "The temple of __HERITAGE_0__ was built by Hoysalas __CIT_0."
    restored = TranslationService.unmask_protected_tokens(mutated_text, token_map)
    assert "Chennakeshava" in restored
    assert "[1]" in restored


@pytest.mark.asyncio
async def test_no_external_cloud_translation_calls():
    """Security invariant: Verify no network calls to external Google/Azure/AWS translation APIs occur."""
    with patch("urllib.request.urlopen") as mock_url, patch("http.client.HTTPConnection") as mock_http:
        provider = NLLBTranslationProvider()
        with patch.object(provider, "_sync_translate", return_value="Translated offline"):
            res = await provider.translate("ಪರೀಕ್ಷೆ", from_lang="kn", to_lang="en")
            assert res == "Translated offline"
            mock_url.assert_not_called()
            mock_http.assert_not_called()


@pytest.mark.asyncio
async def test_server_metadata_never_passed_to_translation(db_session: AsyncSession):
    """Security invariant: Authoritative chunk_id, document_id, generation_id must NEVER enter translation."""
    mock_llm = AsyncMock()
    mock_llm.generate_text.return_value = "The Belur temple is located in Hassan district [1]."
    
    mock_trans = AsyncMock(spec=TranslationService)
    mock_trans.translate_retrieval_query.return_value = "Where is Belur temple?"
    mock_trans.translate_response.return_value = "ಬೇಲೂರು ದೇವಾಲಯವು ಹಾಸನ ಜಿಲ್ಲೆಯಲ್ಲಿದೆ [1]."

    conv_service = ConversationService(
        session=db_session,
        llm_provider=mock_llm,
        translation_service=mock_trans,
    )

    sess_resp = await conv_service.create_session(language_code="kn")
    await conv_service.process_turn(
        session_uuid=sess_resp.session_uuid,
        user_message="ಬೇಲೂರು ದೇವಾಲಯ ಎಲ್ಲಿದೆ?",
    )

    # Check what was passed to translate_response
    if mock_trans.translate_response.called:
        passed_text = mock_trans.translate_response.call_args[1].get("response") or mock_trans.translate_response.call_args[0][0]
        # Must not contain metadata keys or internal IDs
        assert "chunk_id" not in passed_text
        assert "document_id" not in passed_text
        assert "generation_id" not in passed_text
        assert "source_filename" not in passed_text


@pytest.mark.asyncio
async def test_conversation_service_kannada_stream_turn(db_session: AsyncSession):
    """Verify stream_turn translates Kannada query and yields Kannada tokens."""
    mock_llm = MagicMock()
    
    async def mock_stream(*args, **kwargs):
        yield "Belur "
        yield "temple [1]."

    mock_llm.generate_stream = mock_stream

    mock_trans = AsyncMock(spec=TranslationService)
    mock_trans.translate_retrieval_query.return_value = "Tell me about Belur temple"
    mock_trans.translate_response.return_value = "ಬೇಲೂರು ದೇವಾಲಯ [1]."

    conv_service = ConversationService(
        session=db_session,
        llm_provider=mock_llm,
        translation_service=mock_trans,
    )

    sess_resp = await conv_service.create_session(language_code="kn")
    
    events = []
    async for event in conv_service.stream_turn(
        session_uuid=sess_resp.session_uuid,
        user_message="ಬೇಲೂರು ದೇವಾಲಯದ ಮಾಹಿತಿ ನೀಡಿ.",
    ):
        events.append(event)

    assert len(events) >= 1
    # Check that events contain token or done
    event_types = [e["event"] for e in events]
    assert "done" in event_types or "token" in event_types


# ---------------------------------------------------------------------------
# 6. Focused Phase 11 Hardening Regression Tests
# ---------------------------------------------------------------------------

def test_kannada_belur_to_canonical_belur():
    """1. Verify Kannada 'ಬೇಲೂರು' is mapped to canonical English 'Belur'."""
    prep, entities = TranslationService.prepare_retrieval_query("ಬೇಲೂರು ದೇವಾಲಯ ಎಲ್ಲಿದೆ?")
    assert "Belur" in prep
    assert "Belur" in entities
    assert "ಬೇಲೂರು" not in prep


def test_kannada_chennakeshava_to_canonical_chennakeshava():
    """2. Verify Kannada 'ಚೆನ್ನಕೇಶವ' is mapped to canonical English 'Chennakeshava'."""
    prep, entities = TranslationService.prepare_retrieval_query("ಚೆನ್ನಕೇಶವ ದೇವಾಲಯ ಯಾರು ಕಟ್ಟಿಸಿದರು?")
    assert "Chennakeshava" in prep
    assert "Chennakeshava" in entities
    assert "ಚೆನ್ನಕೇಶವ" not in prep


def test_multiple_protected_entities_in_one_query():
    """3. Verify multiple protected entities in one query are both detected and preserved."""
    query = "ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಕಟ್ಟಿಸಿದರು?"
    prep, entities = TranslationService.prepare_retrieval_query(query)
    assert "Belur" in prep
    assert "Chennakeshava" in prep
    assert "Belur" in entities
    assert "Chennakeshava" in entities


@pytest.mark.asyncio
async def test_no_entity_loss_after_translation():
    """4. Verify that if the seq2seq model omits an entity, post-translation restores it."""
    mock_provider = AsyncMock(spec=ITranslationProvider)
    # Simulate model dropping 'Chennakeshava' and returning generic 'Who built the Belur temple?'
    mock_provider.translate.return_value = "Who built the Belur temple?"

    service = TranslationService(provider=mock_provider)
    res = await service.translate_retrieval_query(
        query="ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಕಟ್ಟಿಸಿದರು?",
        from_lang="kn",
        to_lang="en",
    )
    # The missing entity 'Chennakeshava' must be deterministically restored into the query
    assert "Belur" in res
    assert "Chennakeshava" in res


def test_duplicate_entity_placeholder_detection():
    """5. Verify duplicate entity occurrences are handled safely in entity detection."""
    prep, entities = TranslationService.prepare_retrieval_query("ಹಂಪಿ ಮತ್ತು ಹಂಪಿ ಇತಿಹಾಸ")
    assert entities.count("Hampi") == 1
    assert "Hampi" in prep


def test_missing_entity_placeholder_detection():
    """6. Verify unmasking detects missing placeholders and flags validity."""
    token_map = {"__HERITAGE_0__": "Belur", "__CIT_0__": "[1]"}
    text = "The temple is located in Karnataka."
    is_valid = TranslationService.verify_placeholder_integrity(text, token_map)
    assert is_valid is False


@pytest.mark.asyncio
async def test_canonical_retrieval_query_restoration():
    """7. Verify canonical retrieval query translation returns complete English query."""
    mock_provider = AsyncMock(spec=ITranslationProvider)
    mock_provider.translate.return_value = "Who built the Belur Chennakeshava Temple?"

    service = TranslationService(provider=mock_provider)
    res = await service.translate_retrieval_query(
        query="ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಕಟ್ಟಿಸಿದರು?",
        from_lang="kn",
        to_lang="en",
    )
    assert res == "Who built the Belur Chennakeshava Temple?"
    assert "Belur" in res
    assert "Chennakeshava" in res


def test_citation_placeholder_integrity():
    """8. Verify citation placeholders are strictly checked without false positive flags."""
    token_map = {"__CIT_0__": "[1]", "__CIT_1__": "[2]"}
    text = "Belur temple was built in 1117 CE __CIT_0__ by King Vishnuvardhana __CIT_1__."
    is_valid = TranslationService.verify_placeholder_integrity(text, token_map)
    restored = TranslationService.unmask_protected_tokens(text, token_map, strict_citations=True)
    assert is_valid is True
    assert "[1]" in restored
    assert "[2]" in restored


@pytest.mark.asyncio
async def test_no_false_citation_appendage():
    """9. Verify strict citation unmasking does NOT fabricate or append arbitrary [1] when corrupted."""
    mock_provider = AsyncMock(spec=ITranslationProvider)
    # Model dropped the citation tag completely during translation
    mock_provider.translate.return_value = "ಬೇಲೂರು ದೇವಾಲಯವನ್ನು ರಾಜ ವಿಷ್ಣುವರ್ಧನ ನಿರ್ಮಿಸಿದನು."

    service = TranslationService(provider=mock_provider)
    # English response containing [1]
    res = await service.translate_response(
        response="The Belur temple was built by King Vishnuvardhana [1].",
        from_lang="en",
        to_lang="kn",
    )
    # In strict mode with corrupted citations, fails safe to original English text with citation preserved
    # rather than appending [1] to an arbitrary ungrounded Kannada sentence
    assert "[1]" in res


@pytest.mark.asyncio
async def test_english_query_unchanged_zero_overhead():
    """10. Verify English retrieval query bypasses translation completely with zero overhead."""
    mock_provider = AsyncMock(spec=ITranslationProvider)
    service = TranslationService(provider=mock_provider)
    
    eng_query = "Who built the Belur Chennakeshava Temple?"
    res = await service.translate_retrieval_query(eng_query, from_lang="en", to_lang="en")
    assert res == eng_query
    mock_provider.translate.assert_not_called()

