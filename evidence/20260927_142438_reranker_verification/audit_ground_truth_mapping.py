import asyncio
import json
import hashlib
from sqlalchemy import select
from app.infrastructure.db.session import get_session_factory
from app.infrastructure.db.models.chunk import DocumentChunk
from app.infrastructure.db.models.document import Document

async def audit_mapping():
    factory = get_session_factory()
    async with factory() as session:
        # Load all chunks for both generations
        stmt_6ee = select(DocumentChunk).where(
            DocumentChunk.generation_id == '6ee08b45-823a-4bd5-8604-920bbdd61d58'
        ).order_by(DocumentChunk.chunk_index)
        chunks_6ee = (await session.execute(stmt_6ee)).scalars().all()

        stmt_1a2 = select(DocumentChunk).where(
            DocumentChunk.generation_id == '1a2c6365-1bee-4478-9599-a706ee5c7221'
        ).order_by(DocumentChunk.chunk_index)
        chunks_1a2 = (await session.execute(stmt_1a2)).scalars().all()

        # Load documents for filename provenance
        docs = (await session.execute(select(Document))).scalars().all()
        doc_map = {str(d.id): d.filename for d in docs}

        print(f"Total chunks in 6ee: {len(chunks_6ee)}")
        print(f"Total chunks in 1a2: {len(chunks_1a2)}")

        # Check raw equality vs stripped equality
        mapping_records = []
        destination_ids_seen = set()
        ambiguous_matches = []
        unmatched_sources = []

        for c_src in chunks_6ee:
            src_raw = c_src.chunk_text
            src_stripped = src_raw.strip()
            src_raw_sha = hashlib.sha256(src_raw.encode('utf-8')).hexdigest()
            src_stripped_sha = hashlib.sha256(src_stripped.encode('utf-8')).hexdigest()
            src_doc_name = doc_map.get(str(c_src.document_id), str(c_src.document_id))

            exact_raw_matches = []
            stripped_only_matches = []

            for c_dst in chunks_1a2:
                dst_raw = c_dst.chunk_text
                dst_stripped = dst_raw.strip()

                if src_raw == dst_raw:
                    exact_raw_matches.append(c_dst)
                elif src_stripped == dst_stripped:
                    stripped_only_matches.append(c_dst)

            all_matches = exact_raw_matches + stripped_only_matches
            match_count = len(all_matches)

            if match_count == 0:
                unmatched_sources.append(str(c_src.id))
            elif match_count > 1:
                ambiguous_matches.append({
                    "source_id": str(c_src.id),
                    "match_count": match_count,
                    "exact_raw_count": len(exact_raw_matches),
                    "stripped_only_count": len(stripped_only_matches)
                })

            chosen_dst = all_matches[0] if all_matches else None
            dst_id = str(chosen_dst.id) if chosen_dst else None
            if dst_id:
                destination_ids_seen.add(dst_id)

            dst_raw_sha = hashlib.sha256(chosen_dst.chunk_text.encode('utf-8')).hexdigest() if chosen_dst else None
            dst_doc_name = doc_map.get(str(chosen_dst.document_id), str(chosen_dst.document_id)) if chosen_dst else None

            is_exact_raw = (src_raw == chosen_dst.chunk_text) if chosen_dst else False
            is_stripped_equal = (src_stripped == chosen_dst.chunk_text.strip()) if chosen_dst else False

            meta_match = (
                chosen_dst is not None and
                c_src.page_number == chosen_dst.page_number and
                c_src.section_header == chosen_dst.section_header and
                src_doc_name == dst_doc_name
            )

            mapping_records.append({
                "source_6ee_id": str(c_src.id),
                "source_chunk_index": c_src.chunk_index,
                "source_document": src_doc_name,
                "source_page": c_src.page_number,
                "source_section_header": c_src.section_header,
                "source_raw_sha256": src_raw_sha,
                "source_raw_len": len(src_raw),
                "destination_1a2_id": dst_id,
                "destination_chunk_index": chosen_dst.chunk_index if chosen_dst else None,
                "destination_document": dst_doc_name,
                "destination_page": chosen_dst.page_number if chosen_dst else None,
                "destination_section_header": chosen_dst.section_header if chosen_dst else None,
                "destination_raw_sha256": dst_raw_sha,
                "destination_raw_len": len(chosen_dst.chunk_text) if chosen_dst else None,
                "exact_raw_equality": is_exact_raw,
                "stripped_text_equality": is_stripped_equal,
                "metadata_consistent": meta_match,
                "total_candidate_matches": match_count
            })

        print("\n--- Mapping Verification Summary ---")
        print(f"Total source chunks processed: {len(mapping_records)}")
        print(f"Total unique destination IDs matched: {len(destination_ids_seen)} / {len(chunks_1a2)}")
        print(f"Unmatched source chunks: {len(unmatched_sources)}")
        print(f"Ambiguous source chunks (>1 match): {len(ambiguous_matches)}")
        
        raw_eq_count = sum(1 for r in mapping_records if r["exact_raw_equality"])
        stripped_eq_count = sum(1 for r in mapping_records if r["stripped_text_equality"])
        meta_eq_count = sum(1 for r in mapping_records if r["metadata_consistent"])
        
        print(f"Exact raw character-for-character equality: {raw_eq_count} / {len(mapping_records)}")
        print(f"Stripped text equality: {stripped_eq_count} / {len(mapping_records)}")
        print(f"Document, page, and section metadata consistency: {meta_eq_count} / {len(mapping_records)}")

        # Audit expected chunks from canonical_24_queries.json
        with open('/app/scratch/level2_rerank_experiment/canonical_24_queries.json', 'r', encoding='utf-8') as f:
            queries = json.load(f)

        src_id_to_dst = {r["source_6ee_id"]: r["destination_1a2_id"] for r in mapping_records}
        all_expected_6ee_ids = set()
        query_expected_audit = []

        unmapped_expected_ids = []

        for q in queries:
            q_src_ids = q["expected_chunks"]
            q_dst_ids = []
            for sid in q_src_ids:
                all_expected_6ee_ids.add(sid)
                if sid in src_id_to_dst and src_id_to_dst[sid] is not None:
                    q_dst_ids.append(src_id_to_dst[sid])
                else:
                    unmapped_expected_ids.append((q["id"], sid))

            query_expected_audit.append({
                "query_id": q["id"],
                "category": q["category"],
                "query_text": q["query"],
                "expected_chunks_6ee": q_src_ids,
                "expected_chunks_1a2": q_dst_ids,
                "expected_count": len(q_src_ids),
                "mapped_count": len(q_dst_ids),
                "all_mapped": len(q_src_ids) == len(q_dst_ids)
            })

        print(f"\nTotal unique expected 6ee chunk IDs referenced across 24 queries: {len(all_expected_6ee_ids)}")
        print(f"Any unmapped expected chunks? {len(unmapped_expected_ids)}")
        if unmapped_expected_ids:
            print(f"WARNING: Unmapped expected chunks: {unmapped_expected_ids}")
        else:
            print("CONFIRMED: Every original expected chunk was mapped 100% to a valid 1a2 chunk ID!")

        audit_export = {
            "summary": {
                "source_generation_id": "6ee08b45-823a-4bd5-8604-920bbdd61d58",
                "destination_generation_id": "1a2c6365-1bee-4478-9599-a706ee5c7221",
                "source_chunk_count": len(chunks_6ee),
                "destination_chunk_count": len(chunks_1a2),
                "unique_destination_ids_matched": len(destination_ids_seen),
                "is_bijective_1_to_1": len(destination_ids_seen) == len(chunks_1a2) == len(chunks_6ee),
                "exact_raw_equality_count": raw_eq_count,
                "stripped_text_equality_count": stripped_eq_count,
                "metadata_consistent_count": meta_eq_count,
                "total_referenced_expected_chunks": len(all_expected_6ee_ids),
                "unmapped_expected_chunk_count": len(unmapped_expected_ids)
            },
            "chunk_mapping_records": mapping_records,
            "query_expected_chunk_audit": query_expected_audit
        }

        out_path = '/app/scratch/level2_rerank_experiment/mapping_audit.json'
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(audit_export, f, indent=2)
        print(f"Exported mapping audit to {out_path}")

if __name__ == '__main__':
    asyncio.run(audit_mapping())
