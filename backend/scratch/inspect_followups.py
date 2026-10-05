import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.infrastructure.db.models.chat import ChatMessage, SenderType
from app.application.conversation.context_builder import resolve_follow_up_query

# Test all 10 follow-up queries
follow_ups = [
    # Session 1: Belur
    (["Who commissioned the Belur Chennakeshava temple and why?"], "When was it built?", "Belur Chennakeshava Temple"),
    (["Who commissioned the Belur Chennakeshava temple and why?", "When was it built?"], "What soft stone material was used for this monument?", "Belur Chennakeshava Temple"),
    (["Who commissioned the Belur Chennakeshava temple and why?", "When was it built?", "What soft stone material was used for this monument?"], "Tell me about the bracket figures on it", "Belur Chennakeshava Temple"),
    
    # Session 2: Halebidu
    (["Tell me about the Halebidu Hoysaleswara temple complex"], "How many charging war elephants are carved on its base tiers?", "Halebidu Hoysaleswara Temple"),
    (["Tell me about the Halebidu Hoysaleswara temple complex", "How many charging war elephants are carved on its base tiers?"], "Who was the master architect that designed it?", "Halebidu Hoysaleswara Temple"),
    
    # Session 3: Badami Caves
    (["Who established Badami as the capital of the Early Chalukyas?"], "Tell me about the 18-armed Nataraja in this cave complex", "Badami"),
    (["Who established Badami as the capital of the Early Chalukyas?", "Tell me about the 18-armed Nataraja in this cave complex"], "When was Cave 3 carved in it and who commissioned it?", "Badami"),
    
    # Session 4: Aihole
    (["Why is Aihole called the cradle of Indian temple architecture?"], "What is the unique architectural plan of Durga Temple located there?", "Aihole"),
    (["Why is Aihole called the cradle of Indian temple architecture?", "What is the unique architectural plan of Durga Temple located there?"], "Tell me about the Sanskrit inscription found in this complex by poet Ravikirti", "Aihole"),
    
    # Session 5: Pattadakal
    (["Which queen built the Virupaksha temple at Pattadakal?"], "Explain the confluence of Nagara and Dravida styles in this monument complex", "Pattadakal"),
]

for history_texts, query, exp_ctx in follow_ups:
    history_msgs = [ChatMessage(id=str(i), session_id='s', sender_type=SenderType.USER, message_text=t) for i, t in enumerate(history_texts)]
    resolved = resolve_follow_up_query(query, history_msgs)
    passed = exp_ctx.lower() in resolved.lower()
    print(f"[{'PASS' if passed else 'FAIL'}] Q: '{query}' -> Resolved: '{resolved}' (Exp: '{exp_ctx}')")
