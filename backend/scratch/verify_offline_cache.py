"""
Verification script for offline model cache.
Confirms SentenceTransformer('all-MiniLM-L6-v2') loads with local_files_only=True
and produces accurate 384-dimensional embeddings without network access.
"""

import sys
from sentence_transformers import SentenceTransformer

def verify_offline_cache():
    print("Testing offline model loading (local_files_only=True)...")
    try:
        model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
        print("SentenceTransformer loaded successfully with local_files_only=True!")
    except Exception as exc:
        print(f"Failed to load model offline: {exc}", file=sys.stderr)
        sys.exit(1)

    test_sentences = [
        "Mysore Palace is illuminated on Sundays and public holidays.",
        "Hampi Virupaksha temple stands on the south bank of Tungabhadra River."
    ]
    embeddings = model.encode(test_sentences)
    print(f"Generated embeddings shape: {embeddings.shape}")
    assert embeddings.shape == (2, 384), f"Unexpected shape {embeddings.shape}"
    print(f"Embedding dimensions: {embeddings.shape[1]} (expected 384)")
    print("OFFLINE MODEL CACHE VERIFIED: Standalone operation confirmed.")

if __name__ == "__main__":
    verify_offline_cache()
