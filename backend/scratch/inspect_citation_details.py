import asyncio
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.infrastructure.db.session import get_session_factory
from app.application.conversation.service import ConversationService
from scratch.benchmark_conversation import CONVERSATION_SESSIONS_PLAN

async def run_detailed_check():
    sf = get_session_factory()
    async with sf() as session:
        conv = ConversationService(session)
        turn_num = 0
        for s_plan in CONVERSATION_SESSIONS_PLAN:
            s_obj = await conv.create_session(s_plan['initial_lang'])
            print("\n=== " + s_plan['session_name'] + " ===")
            for turn in s_plan['turns']:
                turn_num += 1
                q = turn['query']
                resp = await conv.process_turn(s_obj.session_uuid, q)
                exp_grounded = turn['should_be_grounded']
                exp_doc = turn.get('expected_doc', '')
                exp_page = turn.get('expected_page', None)
                
                cits = [(c.source_filename, c.page_number, round(c.reranker_score, 3) if c.reranker_score else None, c.chunk_id[:8]) for c in resp.citations]
                top_doc = resp.citations[0].source_filename if resp.citations else None
                top_page = resp.citations[0].page_number if resp.citations else None
                
                doc_match = (top_doc == exp_doc) if exp_doc else True
                page_match = (top_page == exp_page) if exp_page else True
                grounded_match = (resp.grounded == exp_grounded)
                
                status = "PASS" if (doc_match and page_match and grounded_match) else "MISMATCH"
                print(f"T{turn_num:02d} [{status:8s}] Q: '{q[:40]}' -> Grounded: {resp.grounded} (exp: {exp_grounded}) | Top Cit: ({top_doc}, p.{top_page}) (exp: {exp_doc}, p.{exp_page})")
                if status == "MISMATCH":
                    print(f"   [!] ResolvedQ: '{resp.retrieval.resolved_query}'")
                    print(f"   [!] Citations emitted: {cits}")
                    if not resp.grounded:
                        print(f"   [!] Ungrounded fallback answer: '{resp.answer}'")

if __name__ == "__main__":
    asyncio.run(run_detailed_check())
