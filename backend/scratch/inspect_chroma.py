"""
Inspect collections in ChromaDB.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.application.knowledge.vector_store import get_chroma_client

def inspect_chroma():
    client = get_chroma_client()
    cols = client.list_collections()
    print(f"ChromaDB Collections ({len(cols)}):")
    for c in cols:
        print(f"  Name: {c.name} | Count: {c.count()} | Metadata: {c.metadata}")

if __name__ == "__main__":
    inspect_chroma()
