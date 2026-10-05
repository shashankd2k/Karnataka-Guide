"""
Unit tests for SentenceTransformers embeddings generation and dimensional stability.
"""

from unittest.mock import MagicMock, patch
import numpy as np
import pytest
from app.application.knowledge.embeddings import (
    generate_embeddings,
    get_embedding_model,
)


def test_generate_embeddings_empty_list():
    result = generate_embeddings([])
    assert result == []


def test_generate_embeddings_validates_dimension():
    # Test error when dimension doesn't match expected 384
    mock_model = MagicMock()
    mock_model.encode.return_value = np.zeros((2, 128), dtype=np.float32)  # Wrong dim: 128 != 384

    with patch("app.application.knowledge.embeddings.get_embedding_model", return_value=mock_model):
        with pytest.raises(ValueError, match="Embedding dimension mismatch"):
            generate_embeddings(["text 1", "text 2"], expected_dimension=384)


def test_generate_embeddings_success_with_mock():
    mock_model = MagicMock()
    mock_model.encode.return_value = np.ones((3, 384), dtype=np.float32)

    with patch("app.application.knowledge.embeddings.get_embedding_model", return_value=mock_model):
        embeddings = generate_embeddings(["Mysore Palace", "Hampi Ruins", "Gol Gumbaz"])
        assert len(embeddings) == 3
        assert len(embeddings[0]) == 384
        assert len(embeddings[1]) == 384
        assert len(embeddings[2]) == 384
