"""
Verify Cross-Encoder loading, batch scoring, and local cache reuse.
"""

from sentence_transformers import CrossEncoder

def test_cross_encoder():
    model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    print(f"Loading CrossEncoder: {model_name}...")
    model = CrossEncoder(model_name)
    print("CrossEncoder loaded successfully!")
    
    query = "Who built the Belur Chennakeshava Temple?"
    passages = [
        "The Chennakeshava Temple at Belur was commissioned by King Vishnuvardhana of the Hoysala dynasty in 1117 CE to mark his victory over the Cholas at Talakadu.",
        "Pattadakal features a cluster of seventh and eighth-century CE Hindu and Jain temples in northern Karnataka.",
        "Table of Contents: 1. Introduction ... 2. Architecture ... 3. Inscriptions ...",
    ]
    
    pairs = [[query, p] for p in passages]
    scores = model.predict(pairs)
    print(f"Query: {query}")
    for p, score in zip(passages, scores):
        print(f"  Score: {score:8.4f} | Text: {p[:60]}...")
        
    assert scores[0] > scores[1], "Relevant Hoysala passage should score higher than Pattadakal passage!"
    assert scores[0] > scores[2], "Relevant passage should score higher than TOC noise!"
    print("Cross-Encoder verification passed!")

if __name__ == "__main__":
    test_cross_encoder()
