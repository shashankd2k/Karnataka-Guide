import asyncio
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from app.infrastructure.db.session import get_session_factory
from app.application.rag.service import RAGRetrievalService
from app.application.rag.schemas import RetrievalDiagnosticRequest

async def analyze_distributions():
    sf = get_session_factory()
    async with sf() as session:
        rag = RAGRetrievalService(session)
        
        # 1. Clearly relevant queries
        clearly_relevant_queries = [
            "Who commissioned the Belur Chennakeshava temple and why?",
            "When was Belur Chennakeshava Temple built?",
            "Tell me about the bracket figures on Belur Chennakeshava Temple",
            "Tell me about the Halebidu Hoysaleswara temple complex",
            "How many charging war elephants are carved on Halebidu Hoysaleswara Temple base tiers?",
            "Who was the master architect that designed Halebidu Hoysaleswara Temple?",
            "Who established Badami as the capital of the Early Chalukyas?",
            "Tell me about the 18-armed Nataraja in Badami cave complex",
            "When was Cave 3 carved in Badami and who commissioned it?",
            "Where is the Bhutanatha temple group located near Badami caves?",
            "Why is Aihole called the cradle of Indian temple architecture?",
            "What is the unique architectural plan of Durga Temple in Aihole?",
            "Tell me about the Sanskrit inscription found in Aihole by poet Ravikirti",
            "Which queen built the Virupaksha temple at Pattadakal?",
            "Explain the confluence of Nagara and Dravida styles at Pattadakal",
            "Which is the oldest surviving temple at Pattadakal?",
            "Who were the founding brothers of the Vijayanagara Empire?",
            "What is special about the 56 pillars in Vijaya Vittala temple?",
            "Describe the monolithic Stone Chariot at Hampi",
            "Belur Chennakeshava ದೇವಾಲಯದಲ್ಲಿರುವ Darpana Sundari ಶಿಲ್ಪದ ಬಗ್ಗೆ ತಿಳಿಸಿ",
            "Halebidu Hoysaleswara temple ನಲ್ಲಿ ಎಷ್ಟು ಆನೆಗಳ ಕೆತ್ತನೆಗಳಿವೆ?",
        ]
        
        # 2. Weakly relevant queries
        weakly_relevant_queries = [
            "What kind of soft stone was used in Karnataka temples?",
            "Are there any caves near lakes in Karnataka?",
            "Tell me about temples with elephant carvings in Karnataka",
            "Who ruled around 1100 AD in southern India?",
            "Where can I see dance poses in rock carvings?",
        ]
        
        # 3. Unsupported / Out-of-domain queries
        unsupported_queries = [
            "What is the capital city of France and how many people live there?",
            "Who won the 2024 ICC T20 cricket world cup?",
            "Explain quantum chromodynamics and quark confinement",
            "How to bake a sourdough pizza crust at home?",
            "Who directed the movie Inception starring Leonardo DiCaprio?",
            "What is the population of Tokyo, Japan in 2026?",
            "Tell me about the history of the Eiffel Tower in Paris",
            "Who is the current prime minister of Australia?",
            "ಪ್ಯಾರಿಸ್ ನಗರದ ಪ್ರವಾಸಿ ಆಕರ್ಷಣೆಗಳ ಬಗ್ಗೆ ಮಾಹಿತಿ ನೀಡಿ",
            "ವಿಶ್ವಕಪ್ ಕ್ರಿಕೆಟ್ ಪಂದ್ಯಾವಳಿಯನ್ನು ಯಾರು ಗೆದ್ದರು?",
        ]
        
        # 4. Pure Kannada queries against English-only corpus
        pure_kannada_queries = [
            "ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಕಟ್ಟಿಸಿದರು?",
            "ಬಾದಾಮಿ ಗುಹೆ 1 ರಲ್ಲಿರುವ 18 ಕೈಗಳ ನಟರಾಜ ಶಿಲ್ಪದ ವಿಶೇಷತೆ ಏನು?",
            "ಐಹೊಳೆ ದುರ್ಗಾ ದೇವಾಲಯದ ವಿಶಿಷ್ಟ ವಾಸ್ತುಶಿಲ್ಪ ಶೈಲಿ ಯಾವುದು?",
            "ಪಟ್ಟದಕಲ್ಲು ವಿರೂಪಾಕ್ಷ ದೇವಾಲಯವನ್ನು ನಿರ್ಮಿಸಿದ ರಾಣಿ ಯಾರು?",
            "ಹಂಪಿ ವಿಜಯ ವಿಠ್ಠಲ ದೇವಾಲಯದ ಸಂಗೀತ ಸ್ತಂಭಗಳ ಬಗ್ಗೆ ತಿಳಿಸಿ",
        ]
        
        async def evaluate_set(name, q_list):
            scores = []
            print(f"\n=== {name} ({len(q_list)} queries) ===")
            for q in q_list:
                req = RetrievalDiagnosticRequest(query=q, top_k=5, rerank_candidates=15, enable_reranker=True)
                res = await rag.retrieve_evidence(req)
                top_score = res.results[0].reranker_score if res.results else -99.0
                scores.append(top_score)
                print(f"  Score: {top_score:+6.3f} | Q: '{q[:48]}'")
            
            scores = np.array(scores)
            print(f"  --> Mean: {scores.mean():+6.3f}, Min: {scores.min():+6.3f}, Max: {scores.max():+6.3f}, Std: {scores.std():.3f}")
            return scores
        
        s_rel = await evaluate_set("CLEARLY RELEVANT QUERIES", clearly_relevant_queries)
        s_weak = await evaluate_set("WEAKLY RELEVANT QUERIES", weakly_relevant_queries)
        s_unsup = await evaluate_set("UNSUPPORTED / OUT-OF-DOMAIN QUERIES", unsupported_queries)
        s_kn = await evaluate_set("PURE KANNADA QUERIES (Cross-Script)", pure_kannada_queries)

if __name__ == "__main__":
    asyncio.run(analyze_distributions())
