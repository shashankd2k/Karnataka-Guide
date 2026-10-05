import os
import socket
import sys
from unittest.mock import MagicMock, patch
from app.core.config import AppProfile, get_settings
from app.application.knowledge.embeddings import get_embedding_model, _MODEL_CACHE
from app.application.rag.reranker import get_cross_encoder_model, _CROSS_ENCODER_CACHE
from sentence_transformers import SentenceTransformer, CrossEncoder

def network_guard(*args, **kwargs):
    raise RuntimeError(f"Network access violation: attempted socket connect to {args}")

def main():
    settings = get_settings()
    print(f"APP_PROFILE: {settings.APP_PROFILE}")
    print(f"HF_HUB_OFFLINE: {os.environ.get('HF_HUB_OFFLINE')}")
    print(f"TRANSFORMERS_OFFLINE: {os.environ.get('TRANSFORMERS_OFFLINE')}")

    is_offline = (settings.APP_PROFILE == AppProfile.STANDALONE or os.environ.get("HF_HUB_OFFLINE") == "1")
    print(f"is_offline evaluated: {is_offline}")
    assert is_offline is True, "Expected offline mode to be active!"

    # 1. Cached embedding model loads locally
    emb_model = get_embedding_model("all-MiniLM-L6-v2")
    assert isinstance(emb_model, SentenceTransformer), "Expected SentenceTransformer instance"
    print("PASS: all-MiniLM-L6-v2 loaded locally from cache")

    # 2. Cached reranker model loads locally
    rerank_model = get_cross_encoder_model("cross-encoder/ms-marco-MiniLM-L-6-v2")
    assert isinstance(rerank_model, CrossEncoder), "Expected CrossEncoder instance"
    print("PASS: cross-encoder/ms-marco-MiniLM-L-6-v2 loaded locally from cache")

    # 3. Missing embedding model in offline mode with network guard
    # Strict try/except OSError/else pattern:
    # - If no exception is raised, else branch triggers test failure.
    # - If an unrelated exception (TypeError, AssertionError, etc.) is raised, it is NOT caught and aborts.
    _MODEL_CACHE.pop("nonexistent-dummy-emb", None)
    with patch("socket.socket.connect", side_effect=network_guard):
        try:
            get_embedding_model("nonexistent-dummy-emb")
        except OSError as exc:
            exc_str = str(exc)
            print(f"Caught expected OSError: {exc_str[:120]}...")
            assert "local_files_only" in exc_str or "Cannot find" in exc_str or "couldn't find" in exc_str.lower(), (
                f"Unexpected OSError message: {exc_str}"
            )
            print("PASS: Missing embedding model raised OSError (local_files_only) with zero network attempts.")
        else:
            raise AssertionError("FAIL: get_embedding_model did NOT raise OSError on missing model in offline mode!")

    # 4. Missing reranker model in offline mode with network guard
    _CROSS_ENCODER_CACHE.pop("nonexistent-dummy-rerank", None)
    with patch("socket.socket.connect", side_effect=network_guard):
        try:
            get_cross_encoder_model("nonexistent-dummy-rerank")
        except OSError as exc:
            exc_str = str(exc)
            print(f"Caught expected OSError: {exc_str[:120]}...")
            assert "local_files_only" in exc_str or "Cannot find" in exc_str or "couldn't find" in exc_str.lower(), (
                f"Unexpected OSError message: {exc_str}"
            )
            print("PASS: Missing reranker model raised OSError (local_files_only) with zero network attempts.")
        else:
            raise AssertionError("FAIL: get_cross_encoder_model did NOT raise OSError on missing model in offline mode!")

    # 5. Verify the offline branch NEVER calls unrestricted online fallback
    print("\nVerifying offline branch execution path using controlled mocks...")
    
    # Test embeddings: simulate local_files_only=True raising OSError
    _MODEL_CACHE.pop("test-offline-branch-emb", None)
    mock_st_class = MagicMock(side_effect=OSError("Simulated offline local cache miss"))
    with patch("sentence_transformers.SentenceTransformer", mock_st_class):
        try:
            get_embedding_model("test-offline-branch-emb")
        except OSError:
            # Verify SentenceTransformer was called EXACTLY ONCE with local_files_only=True
            assert mock_st_class.call_count == 1, f"Expected exactly 1 call, got {mock_st_class.call_count}"
            _, kwargs = mock_st_class.call_args
            assert kwargs.get("local_files_only") is True, f"Expected local_files_only=True, got {kwargs}"
            print("PASS: get_embedding_model called constructor strictly once with local_files_only=True; no unrestricted fallback attempted.")
        else:
            raise AssertionError("FAIL: get_embedding_model did not propagate OSError from simulated cache miss!")

    # Test reranker: simulate local_files_only=True raising OSError
    _CROSS_ENCODER_CACHE.pop("test-offline-branch-rerank", None)
    mock_ce_class = MagicMock(side_effect=OSError("Simulated offline local cache miss"))
    with patch("sentence_transformers.CrossEncoder", mock_ce_class):
        try:
            get_cross_encoder_model("test-offline-branch-rerank")
        except OSError:
            # Verify CrossEncoder was called EXACTLY ONCE with local_files_only=True
            assert mock_ce_class.call_count == 1, f"Expected exactly 1 call, got {mock_ce_class.call_count}"
            _, kwargs = mock_ce_class.call_args
            assert kwargs.get("local_files_only") is True, f"Expected local_files_only=True, got {kwargs}"
            print("PASS: get_cross_encoder_model called constructor strictly once with local_files_only=True; no unrestricted fallback attempted.")
        else:
            raise AssertionError("FAIL: get_cross_encoder_model did not propagate OSError from simulated cache miss!")

    print("\nALL OFFLINE LOADER AND DEFECT-FREE VERIFICATION CHECKS PASSED.")

if __name__ == "__main__":
    main()
