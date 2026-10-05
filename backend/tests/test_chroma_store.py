"""
Unit tests for ChromaDB persistent vector storage, collection partitioning, and query mapping.
"""

from pathlib import Path
from app.application.knowledge.vector_store import (
    delete_generation_collection,
    get_chroma_client,
    get_collection_name,
    get_generation_collection_count,
    get_or_create_generation_collection,
    index_chunks_into_chroma,
)


def test_get_collection_name_sanitizes_hyphens():
    gen_id = "123e4567-e89b-12d3-a456-426614174000"
    col_name = get_collection_name(gen_id)
    assert col_name == "gen_123e4567_e89b_12d3_a456_426614174000"
    assert "-" not in col_name


def test_chroma_persistent_indexing_and_isolation(tmp_path: Path):
    client = get_chroma_client(persist_path=tmp_path)
    gen_id_1 = "gen-test-001"
    gen_id_2 = "gen-test-002"

    chunk_ids = ["chunk-1", "chunk-2"]
    vectors = [
        [1.0] + [0.0] * 383,
        [0.0] + [1.0] * 383,
    ]
    docs = ["Mysore Palace is illuminated on Sundays.", "Hampi Virupaksha temple is active."]
    metadatas = [
        {"doc_id": "doc-1", "page": 1, "section": "Palaces"},
        {"doc_id": "doc-1", "page": 2, "section": "Temples"},
    ]

    # Index into generation 1
    indexed_count = index_chunks_into_chroma(
        generation_id=gen_id_1,
        chunk_ids=chunk_ids,
        embeddings=vectors,
        documents=docs,
        metadatas=metadatas,
        client=client,
    )
    assert indexed_count == 2
    assert get_generation_collection_count(gen_id_1, client=client) == 2

    # Generation 2 collection should be isolated and empty
    assert get_generation_collection_count(gen_id_2, client=client) == 0

    # Query generation 1
    col1 = get_or_create_generation_collection(gen_id_1, client=client)
    res = col1.query(query_embeddings=[[1.0] + [0.0] * 383], n_results=1)
    assert len(res["ids"][0]) == 1
    assert res["ids"][0][0] == "chunk-1"

    # Delete collection
    deleted = delete_generation_collection(gen_id_1, client=client)
    assert deleted is True
    assert get_generation_collection_count(gen_id_1, client=client) == 0
