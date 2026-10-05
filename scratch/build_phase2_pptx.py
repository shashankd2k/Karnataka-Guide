import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

# 16:9 widescreen dimensions
SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)

# Color Palette
COLOR_PRIMARY_DARK = RGBColor(15, 23, 42)    # Slate 900
COLOR_HEADER_BLUE  = RGBColor(30, 58, 138)   # Royal Blue 900
COLOR_ACCENT_GOLD  = RGBColor(180, 83, 9)    # Hoysala Amber/Gold 700
COLOR_TEXT_MAIN    = RGBColor(51, 65, 85)    # Slate 700
COLOR_TEXT_MUTED   = RGBColor(100, 116, 139) # Slate 500
COLOR_CARD_BG      = RGBColor(248, 250, 252) # Slate 50
COLOR_CARD_BORDER  = RGBColor(226, 232, 240) # Slate 200
COLOR_WHITE        = RGBColor(255, 255, 255)
COLOR_SUCCESS_GREEN= RGBColor(22, 101, 52)   # Green 800
COLOR_PILL_BG      = RGBColor(238, 242, 255) # Indigo 50
COLOR_PILL_TEXT    = RGBColor(67, 56, 202)   # Indigo 700

ARTIFACTS_DIR = r"C:\Users\91998\.gemini\antigravity-ide\brain\9d5221e9-c7d6-42bd-b938-d25868ed0951"
OUTPUT_PPTX_PATH = r"d:\Karnataka Guide\SMART_TOURIST_GUIDE_BELURU_CHENNAKESHAVA_TEMPLE_PHASE2.pptx"

def create_deck():
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    blank_layout = prs.slide_layouts[6] # completely blank

    def add_header(slide, category_tag, slide_title):
        # Category Tag
        tag_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.35))
        tf_tag = tag_box.text_frame
        tf_tag.word_wrap = True
        tf_tag.margin_left = tf_tag.margin_right = tf_tag.margin_top = tf_tag.margin_bottom = 0
        p_tag = tf_tag.paragraphs[0]
        p_tag.text = category_tag.upper()
        p_tag.font.size = Pt(11)
        p_tag.font.bold = True
        p_tag.font.color.rgb = COLOR_ACCENT_GOLD

        # Slide Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.75), Inches(11.7), Inches(0.65))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        tf_title.margin_left = tf_title.margin_right = tf_title.margin_top = tf_title.margin_bottom = 0
        p_title = tf_title.paragraphs[0]
        p_title.text = slide_title
        p_title.font.size = Pt(22)
        p_title.font.bold = True
        p_title.font.color.rgb = COLOR_HEADER_BLUE

        # Subtle divider line
        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.42), Inches(11.733), Inches(0.02))
        line.fill.solid()
        line.fill.fore_color.rgb = COLOR_CARD_BORDER
        line.line.color.rgb = COLOR_CARD_BORDER

    # ==========================================
    # SLIDE 1: TITLE SLIDE
    # ==========================================
    s1 = prs.slides.add_slide(blank_layout)
    
    # Background banner top
    banner = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.2))
    banner.fill.solid()
    banner.fill.fore_color.rgb = COLOR_ACCENT_GOLD
    banner.line.color.rgb = COLOR_ACCENT_GOLD

    # Title Box
    t_box = s1.shapes.add_textbox(Inches(1.0), Inches(0.8), Inches(11.333), Inches(1.8))
    tf1 = t_box.text_frame
    tf1.word_wrap = True
    p0 = tf1.paragraphs[0]
    p0.text = "PHASE-II MAJOR PROJECT PRESENTATION"
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = COLOR_ACCENT_GOLD

    p1 = tf1.add_paragraph()
    p1.text = "SMART TOURIST GUIDE FOR BELURU CHENNAKESHAVA TEMPLE"
    p1.font.size = Pt(28)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_PRIMARY_DARK
    p1.space_before = Pt(8)

    p2 = tf1.add_paragraph()
    p2.text = "Software-Based AI Tourist Assistance System with Hybrid RAG & Offline Local LLM"
    p2.font.size = Pt(15)
    p2.font.color.rgb = COLOR_HEADER_BLUE
    p2.space_before = Pt(4)

    # Description Card
    desc_card = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(2.7), Inches(11.333), Inches(2.7))
    desc_card.fill.solid()
    desc_card.fill.fore_color.rgb = COLOR_CARD_BG
    desc_card.line.color.rgb = COLOR_CARD_BORDER

    desc_tf = desc_card.text_frame
    desc_tf.word_wrap = True
    desc_tf.margin_left = Inches(0.4)
    desc_tf.margin_right = Inches(0.4)
    desc_tf.margin_top = Inches(0.3)
    desc_tf.margin_bottom = Inches(0.3)

    dp0 = desc_tf.paragraphs[0]
    dp0.text = "PROJECT OVERVIEW & SYSTEM DESCRIPTION"
    dp0.font.size = Pt(12)
    dp0.font.bold = True
    dp0.font.color.rgb = COLOR_ACCENT_GOLD

    dp1 = desc_tf.add_paragraph()
    dp1.text = ("Smart Tourist Guide for Beluru Chennakeshava Temple is a software-based AI tourist assistance system "
                "designed to provide accurate, multilingual and interactive information to visitors. The system supports "
                "Kannada and English text and voice interaction and uses Retrieval-Augmented Generation (RAG), Natural Language "
                "Processing, a local Large Language Model, embeddings and ChromaDB to retrieve information from a verified "
                "temple-specific knowledge base. It provides grounded answers about the temple's history, architecture, "
                "sculptures, visitor guidelines and nearby attractions while reducing incorrect or unsupported information. "
                "The system also supports source citations, speech-to-text, text-to-speech and offline operation to improve "
                "accessibility and visitor experience.")
    dp1.font.size = Pt(13.5)
    dp1.font.color.rgb = COLOR_TEXT_MAIN
    dp1.space_before = Pt(8)

    # Key Badges at bottom
    badges = [
        "100% Software-Based",
        "100% Local / Offline AI (Zero Cloud Calls)",
        "Zero-Login Public Access",
        "Strict Grounding & Hallucination Guard"
    ]
    bx = Inches(1.0)
    for b in badges:
        b_shape = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, bx, Inches(5.8), Inches(2.65), Inches(0.6))
        b_shape.fill.solid()
        b_shape.fill.fore_color.rgb = COLOR_PILL_BG
        b_shape.line.color.rgb = COLOR_CARD_BORDER
        btf = b_shape.text_frame
        btf.word_wrap = True
        bp = btf.paragraphs[0]
        bp.text = b
        bp.font.size = Pt(10.5)
        bp.font.bold = True
        bp.font.color.rgb = COLOR_PILL_TEXT
        bp.alignment = PP_ALIGN.CENTER
        bx += Inches(2.88)

    # ==========================================
    # SLIDE 2: PRESENTATION OUTLINE
    # ==========================================
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "PRESENTATION ROADMAP", "Project Presentation Phase II Slides Outline")

    sections = [
        ("01. Module Description (Part I)", "Modules 1 to 4: Tourist Conversational Interface, Knowledge Management, Hybrid RAG, Grounded LLM"),
        ("02. Module Description (Part II)", "Modules 5 to 8: Multilingual Translation, Voice STT/TTS, Temple Attractions Map, Admin Security"),
        ("03. Implementation Workflow", "Important implementation steps: End-to-end 8-stage pipeline from Tourist Query to Verified Response"),
        ("04. Key Algorithms", "Reciprocal Rank Fusion (k=60), Cross-Encoder Reranker, Okapi BM25, S-BERT, CTranslate2 int8, Argon2id"),
        ("05. Experimental Results", "Retrieval Quality (Hit@1 100%, MRR 1.0), Zero Hallucination Grounding, 330/330 Unit/Integration Tests"),
        ("06. Graphical Portrayal", "System Architecture, DFD Level 1, Use Case, ER Diagram, RAG Flowchart, Docker Deployment, UI Screens"),
        ("07. Conclusion & Future Scope", "System benefits, local AI cultural preservation impact, and future optimization roadmap"),
        ("08. References", "Academic literature and official technical documentation for all underlying models and frameworks")
    ]

    for i, (title, sub) in enumerate(sections):
        col = i % 2
        row = i // 2
        cx = Inches(0.8 + col * 5.95)
        cy = Inches(1.65 + row * 1.32)

        card = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, cx, cy, Inches(5.75), Inches(1.18))
        card.fill.solid()
        card.fill.fore_color.rgb = COLOR_CARD_BG
        card.line.color.rgb = COLOR_CARD_BORDER

        ctf = card.text_frame
        ctf.word_wrap = True
        ctf.margin_left = ctf.margin_right = Inches(0.25)
        ctf.margin_top = Inches(0.18)

        cp0 = ctf.paragraphs[0]
        cp0.text = title
        cp0.font.size = Pt(13)
        cp0.font.bold = True
        cp0.font.color.rgb = COLOR_HEADER_BLUE

        cp1 = ctf.add_paragraph()
        cp1.text = sub
        cp1.font.size = Pt(11)
        cp1.font.color.rgb = COLOR_TEXT_MAIN
        cp1.space_before = Pt(3)

    # ==========================================
    # SLIDE 3: MODULE DESCRIPTION - PART I
    # ==========================================
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "MODULE DESCRIPTION — PART I", "Core Architecture & Conversational Intelligence")

    mods_p1 = [
        ("Module 1: Tourist Conversational Interface",
         ["• Zero-login, public access designed for on-site Beluru temple tourists (no login barriers).",
          "• Supports bilingual (English & Kannada) text chat with real-time SSE token streaming.",
          "• Multi-turn session context: tracks last 5 conversation turns to resolve follow-up queries."]),
        ("Module 2: Knowledge Base & Document Management",
         ["• Upload verified Beluru Chennakeshava Temple research papers, ASI guides, and architectural records.",
          "• Enforces strict SHA-256 deduplication, MIME validation (application/pdf), and UUID storage.",
          "• Immutable knowledge generation pipeline ensures zero corruption of active knowledge."]),
        ("Module 3: Hybrid RAG Retrieval Engine",
         ["• Parallel retrieval: Dense vector search in ChromaDB (MiniLM-L6-v2) + Sparse BM25 keyword search.",
          "• Reciprocal Rank Fusion (RRF, k=60) merges semantic intent and exact temple terminology.",
          "• Cross-Encoder neural reranking (ms-marco-MiniLM-L-6-v2) isolates the top 5 most relevant passages."]),
        ("Module 4: Grounded LLM Response Generation",
         ["• Local Ollama LLM server running phi3:mini (3.8B parameters) with prompt injection defense.",
          "• Grounding Guard (score >= -6.0): returns safe bilingual fallback if evidence is insufficient.",
          "• Server-authoritative citations: inline markers [1], [2] linked to verified database chunks."])
    ]

    for i, (title, bullets) in enumerate(mods_p1):
        col = i % 2
        row = i // 2
        cx = Inches(0.8 + col * 5.95)
        cy = Inches(1.65 + row * 2.7)

        card = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, cx, cy, Inches(5.75), Inches(2.55))
        card.fill.solid()
        card.fill.fore_color.rgb = COLOR_CARD_BG
        card.line.color.rgb = COLOR_CARD_BORDER

        ctf = card.text_frame
        ctf.word_wrap = True
        ctf.margin_left = ctf.margin_right = Inches(0.25)
        ctf.margin_top = Inches(0.2)

        cp0 = ctf.paragraphs[0]
        cp0.text = title
        cp0.font.size = Pt(13)
        cp0.font.bold = True
        cp0.font.color.rgb = COLOR_HEADER_BLUE

        for b in bullets:
            bp = ctf.add_paragraph()
            bp.text = b
            bp.font.size = Pt(11)
            bp.font.color.rgb = COLOR_TEXT_MAIN
            bp.space_before = Pt(4)

    # ==========================================
    # SLIDE 4: MODULE DESCRIPTION - PART II
    # ==========================================
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, "MODULE DESCRIPTION — PART II", "Multilingual, Voice, Heritage Discovery & Administration")

    mods_p2 = [
        ("Module 5: Multilingual & Translation Engine",
         ["• Meta NLLB-200 (600M) neural model running offline for Kannada <-> English translation.",
          "• Unicode script analysis (U+0C80–U+0CFF) for instant, zero-latency Kannada language detection.",
          "• Preserves temple proper nouns (Chennakeshava, Shantala Devi, Darpana Sundari, Hoysala)."]),
        ("Module 6: Voice Processing Engine (STT & TTS)",
         ["• Faster-Whisper (CTranslate2 int8 on CPU) converts English and Kannada speech to text.",
          "• Piper ONNX TTS synthesizes natural English audio; Meta MMS-TTS synthesizes Kannada.",
          "• Audio playback strictly bound to server-validated assistant messages to prevent spoofing."]),
        ("Module 7: Temple Attractions & Interactive Map",
         ["• Interactive Leaflet map of Beluru temple complex with custom Hoysala Kalasha markers.",
          "• Curated profiles for 42 Madanika bracket figures, Star-shaped Jagati platform, Narasimha pillar.",
          "• Suggested query pills for one-tap exploration of temple history, timings, and rituals."]),
        ("Module 8: Admin Dashboard & System Security",
         ["• 4-tier Role-Based Access Control (SUPER_ADMIN, SITE_CURATOR, OPERATOR, VIEWER).",
          "• Argon2id password hashing + rotating JWT authentication for administrative operations.",
          "• RAG Diagnostics Workbench to inspect Dense/BM25 scores and trigger instant rollback."])
    ]

    for i, (title, bullets) in enumerate(mods_p2):
        col = i % 2
        row = i // 2
        cx = Inches(0.8 + col * 5.95)
        cy = Inches(1.65 + row * 2.7)

        card = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, cx, cy, Inches(5.75), Inches(2.55))
        card.fill.solid()
        card.fill.fore_color.rgb = COLOR_CARD_BG
        card.line.color.rgb = COLOR_CARD_BORDER

        ctf = card.text_frame
        ctf.word_wrap = True
        ctf.margin_left = ctf.margin_right = Inches(0.25)
        ctf.margin_top = Inches(0.2)

        cp0 = ctf.paragraphs[0]
        cp0.text = title
        cp0.font.size = Pt(13)
        cp0.font.bold = True
        cp0.font.color.rgb = COLOR_HEADER_BLUE

        for b in bullets:
            bp = ctf.add_paragraph()
            bp.text = b
            bp.font.size = Pt(11)
            bp.font.color.rgb = COLOR_TEXT_MAIN
            bp.space_before = Pt(4)

    # ==========================================
    # SLIDE 5: IMPLEMENTATION WORKFLOW
    # ==========================================
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, "TECHNICAL IMPLEMENTATION", "Important Implementation Steps: End-to-End Processing Flow")

    steps = [
        ("Step 1: Ingestion & Normalization", "Admins upload verified Beluru PDFs. Text is extracted via PyMuPDF, normalized to Unicode NFC, and chunked into ~800 char semantic segments with 120 char overlap."),
        ("Step 2: Vector Indexing & ChromaDB", "Chunk embeddings generated via all-MiniLM-L6-v2 (384-dim). Indexed into isolated generation-specific ChromaDB collections with MySQL metadata synchronization."),
        ("Step 3: Query & Language Detection", "User query (text or voice) inspected via Unicode script detection. If voice, Faster-Whisper transcribes audio. If Kannada, NLLB-200 translates query to English for retrieval."),
        ("Step 4: Parallel Hybrid Retrieval", "Simultaneous dense vector search (ChromaDB) and sparse keyword search (Okapi BM25). Merged using Reciprocal Rank Fusion (RRF, k=60) from top-25 candidates each."),
        ("Step 5: Cross-Encoder Reranking", "Neural Cross-Encoder (ms-marco-MiniLM-L-6-v2) scores top-15 fused chunks. Selects top-5 most relevant chunks with joint query-passage attention."),
        ("Step 6: Grounding Guard Verification", "Evaluates top score against strict threshold (>= -6.0). If insufficient evidence, returns safe bilingual fallback without invoking LLM, preventing hallucination."),
        ("Step 7: Local LLM Generation & SSE", "Ollama phi3:mini generates grounded 2-4 sentence response using retrieved context only. Real-time token streaming delivered via Server-Sent Events (SSE)."),
        ("Step 8: Multimodal Delivery & TTS", "Citations verified against MySQL. If Kannada session, response translated via NLLB-200. Piper/MMS-TTS synthesizes audio on demand.")
    ]

    for i, (title, desc) in enumerate(steps):
        col = i % 2
        row = i // 2
        cx = Inches(0.8 + col * 5.95)
        cy = Inches(1.65 + row * 1.35)

        card = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, cx, cy, Inches(5.75), Inches(1.22))
        card.fill.solid()
        card.fill.fore_color.rgb = COLOR_CARD_BG
        card.line.color.rgb = COLOR_CARD_BORDER

        ctf = card.text_frame
        ctf.word_wrap = True
        ctf.margin_left = ctf.margin_right = Inches(0.22)
        ctf.margin_top = Inches(0.14)

        cp0 = ctf.paragraphs[0]
        cp0.text = title
        cp0.font.size = Pt(12)
        cp0.font.bold = True
        cp0.font.color.rgb = COLOR_HEADER_BLUE

        cp1 = ctf.add_paragraph()
        cp1.text = desc
        cp1.font.size = Pt(10.5)
        cp1.font.color.rgb = COLOR_TEXT_MAIN
        cp1.space_before = Pt(2)

    # ==========================================
    # SLIDE 6: KEY ALGORITHMS & FORMULATIONS
    # ==========================================
    s6 = prs.slides.add_slide(blank_layout)
    add_header(s6, "TECHNICAL IMPLEMENTATION", "Key Algorithms & Mathematical Formulations")

    # Table of Algorithms
    rows, cols = 7, 4
    left = Inches(0.8)
    top = Inches(1.7)
    width = Inches(11.733)
    height = Inches(5.2)

    table_shape = s6.shapes.add_table(rows, cols, left, top, width, height)
    table = table_shape.table
    table.columns[0].width = Inches(2.2)
    table.columns[1].width = Inches(1.8)
    table.columns[2].width = Inches(3.8)
    table.columns[3].width = Inches(3.933)

    headers = ["Algorithm / Model", "Pipeline Stage", "Mathematical / Technical Basis", "Role in Temple Guide Platform"]
    for col_idx, h in enumerate(headers):
        cell = table.cell(0, col_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = COLOR_HEADER_BLUE
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        p.text = h
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = COLOR_WHITE

    algo_data = [
        ("Reciprocal Rank Fusion (RRF)", "Hybrid Retrieval", "RRF(d) = Σ 1 / (60 + r_m(d))", "Fuses dense vector semantics and BM25 sparse keyword rankings without score normalization bias."),
        ("Cross-Encoder Reranking", "Evidence Scoring", "s(q, d) = Softmax(W · BERT(q ○ d))", "Joint self-attention over query + chunk text; identifies the top 5 most factual evidence chunks."),
        ("Okapi BM25 Keyword Search", "Sparse Retrieval", "Score = Σ IDF · (f · (k1+1)) / (f + k1·(1-b+b·|D|/avgdl))", "Accurately retrieves exact temple historical entities, king names, and architectural terms."),
        ("Sentence-BERT (MiniLM-L6)", "Vector Embeddings", "E(t) = MeanPool(Transformer(t)), 384-dim", "Dense semantic representation capturing contextual meaning in ChromaDB vector space."),
        ("Faster-Whisper (CTranslate2)", "Speech-to-Text", "8-bit integer quantization (int8) on CPU", "Enables local offline speech transcription in English and Kannada with low RAM usage."),
        ("Argon2id Key Derivation", "Security & Auth", "Memory-hard hashing (m=65536, t=3, p=4)", "Protects admin accounts against GPU-accelerated dictionary and rainbow table attacks.")
    ]

    for row_idx, row in enumerate(algo_data):
        for col_idx, text in enumerate(row):
            cell = table.cell(row_idx + 1, col_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = COLOR_CARD_BG if row_idx % 2 == 0 else COLOR_WHITE
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = cell.text_frame.paragraphs[0]
            p.text = text
            p.font.size = Pt(10)
            p.font.color.rgb = COLOR_TEXT_MAIN
            if col_idx == 0:
                p.font.bold = True
                p.font.color.rgb = COLOR_HEADER_BLUE

    # ==========================================
    # SLIDE 7: RESULTS & PERFORMANCE METRICS
    # ==========================================
    s7 = prs.slides.add_slide(blank_layout)
    add_header(s7, "SYSTEM EVALUATION & BENCHMARKS", "Experimental Results & Verification Metrics")

    # 4 Metric Highlight Cards on Top
    metric_cards = [
        ("100.0%", "Hit@1 Retrieval Rate", "Relevant passage ranked #1 across all tests"),
        ("1.0000", "Mean Reciprocal Rank", "Optimal ranking efficiency in Hybrid RAG"),
        ("100%", "Grounding Accuracy", "Zero hallucinations across 30-turn evaluation"),
        ("330 / 330", "Test Suite Pass Rate", "100% backend (283) & frontend (47) tests")
    ]

    mx = Inches(0.8)
    for num, lbl, sub in metric_cards:
        mcard = s7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, mx, Inches(1.65), Inches(2.78), Inches(1.4))
        mcard.fill.solid()
        mcard.fill.fore_color.rgb = COLOR_CARD_BG
        mcard.line.color.rgb = COLOR_CARD_BORDER

        mtf = mcard.text_frame
        mtf.word_wrap = True
        mtf.margin_top = Inches(0.15)

        mp0 = mtf.paragraphs[0]
        mp0.text = num
        mp0.font.size = Pt(22)
        mp0.font.bold = True
        mp0.font.color.rgb = COLOR_SUCCESS_GREEN
        mp0.alignment = PP_ALIGN.CENTER

        mp1 = mtf.add_paragraph()
        mp1.text = lbl
        mp1.font.size = Pt(11)
        mp1.font.bold = True
        mp1.font.color.rgb = COLOR_HEADER_BLUE
        mp1.alignment = PP_ALIGN.CENTER

        mp2 = mtf.add_paragraph()
        mp2.text = sub
        mp2.font.size = Pt(9.5)
        mp2.font.color.rgb = COLOR_TEXT_MUTED
        mp2.alignment = PP_ALIGN.CENTER
        mx += Inches(2.98)

    # Detailed Result Sections Below
    detailed_results = [
        ("Retrieval & Grounding Accuracy",
         ["• Hit@1 = 100.0%, Recall@5 = 100.0%, MRR = 1.0000 across verified temple knowledge corpus.",
          "• Grounding Guard achieved 100% precision: 0 hallucinations and 0 bibliography leakage.",
          "• 100% server-authoritative citation verification (44/44 citations verified against MySQL chunks)."]),
        ("Offline AI Execution & Deployment",
         ["• 100% verified offline standalone operation — all 7 models load with zero internet access.",
          "• 4-container Docker Compose stack (Backend, Nginx Frontend, MySQL 8.0, Ollama) verified healthy.",
          "• Voice pipeline operational (English & Kannada); conversational latency optimization in progress."])
    ]

    for i, (title, bullets) in enumerate(detailed_results):
        cx = Inches(0.8 + i * 5.95)
        card = s7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, cx, Inches(3.3), Inches(5.75), Inches(3.55))
        card.fill.solid()
        card.fill.fore_color.rgb = COLOR_CARD_BG
        card.line.color.rgb = COLOR_CARD_BORDER

        ctf = card.text_frame
        ctf.word_wrap = True
        ctf.margin_left = ctf.margin_right = Inches(0.28)
        ctf.margin_top = Inches(0.25)

        cp0 = ctf.paragraphs[0]
        cp0.text = title
        cp0.font.size = Pt(14)
        cp0.font.bold = True
        cp0.font.color.rgb = COLOR_HEADER_BLUE

        for b in bullets:
            bp = ctf.add_paragraph()
            bp.text = b
            bp.font.size = Pt(11.5)
            bp.font.color.rgb = COLOR_TEXT_MAIN
            bp.space_before = Pt(8)

    # Helper function to add diagram slides with full-width image & side notes
    def add_diagram_slide(category, title, img_filename, key_points, is_portrait=False):
        s = prs.slides.add_slide(blank_layout)
        add_header(s, category, title)
        img_path = os.path.join(ARTIFACTS_DIR, img_filename)

        if os.path.exists(img_path):
            if is_portrait:
                # Place image on left (4.5 in width), text on right (7.0 in width)
                s.shapes.add_picture(img_path, Inches(0.8), Inches(1.65), width=Inches(4.2))
                card_x = Inches(5.2)
                card_w = Inches(7.333)
            else:
                # Landscape image on left (7.8 in width), text on right (3.7 in width)
                s.shapes.add_picture(img_path, Inches(0.8), Inches(1.65), width=Inches(7.8))
                card_x = Inches(8.8)
                card_w = Inches(3.733)

            # Description Card on the side
            side_card = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, card_x, Inches(1.65), card_w, Inches(5.2))
            side_card.fill.solid()
            side_card.fill.fore_color.rgb = COLOR_CARD_BG
            side_card.line.color.rgb = COLOR_CARD_BORDER

            tf = side_card.text_frame
            tf.word_wrap = True
            tf.margin_left = tf.margin_right = Inches(0.25)
            tf.margin_top = Inches(0.25)

            p0 = tf.paragraphs[0]
            p0.text = "ARCHITECTURAL HIGHLIGHTS"
            p0.font.size = Pt(12)
            p0.font.bold = True
            p0.font.color.rgb = COLOR_ACCENT_GOLD

            for kp in key_points:
                p = tf.add_paragraph()
                p.text = kp
                p.font.size = Pt(10.5)
                p.font.color.rgb = COLOR_TEXT_MAIN
                p.space_before = Pt(6)
        else:
            print(f"Warning: Image not found: {img_path}")

    # ==========================================
    # SLIDE 8: SYSTEM ARCHITECTURE DIAGRAM
    # ==========================================
    add_diagram_slide(
        "GRAPHICAL PORTRAYAL — SOFTWARE ARCHITECTURE",
        "System Architecture: 4-Layer Clean Architecture",
        "renamed_architecture_1789928477908.jpg",
        [
            "• Layer 1 (Presentation): React 19 Tourist SPA (Chat, Voice, Map, Citations) and Admin Dashboard.",
            "• Layer 2 (API Gateway): FastAPI at /api/v1 with rate limiting, CORS, JWT auth, and SSE token streaming.",
            "• Layer 3 (Application): Decoupled business logic (Conversation, RAG, Speech, Translation, Auth).",
            "• Layer 4 (Infrastructure): MySQL 8.0, ChromaDB, Ollama (phi3:mini), Faster-Whisper, Piper & MMS-TTS.",
            "• 100% Offline AI: All AI models run locally with zero cloud API dependencies."
        ]
    )

    # ==========================================
    # SLIDE 9: DATA FLOW DIAGRAM (DFD LEVEL 1)
    # ==========================================
    add_diagram_slide(
        "GRAPHICAL PORTRAYAL — DATA FLOW DIAGRAM",
        "Data Flow Diagram (DFD Level 1): Processes & Data Stores",
        "renamed_dfd_1789928913178.jpg",
        [
            "• External Entities: Tourist (zero login required) and Admin (authenticated via JWT).",
            "• 7 Core Processes: Language Detection, Hybrid RAG Retrieval, Grounding Guard & LLM, Translation, Voice STT/TTS, Document Ingestion, and RBAC.",
            "• 3 Permanent Stores: MySQL 8.0 (chunks, sessions, messages), ChromaDB (vectors), and PDF Storage.",
            "• Verifiable Feedback Loop: Grounding Guard checks evidence before invoking LLM."
        ]
    )

    # ==========================================
    # SLIDE 10: UML USE CASE DIAGRAM
    # ==========================================
    add_diagram_slide(
        "GRAPHICAL PORTRAYAL — USE CASE MODEL",
        "UML Use Case Diagram: Tourist & Admin Functional Capabilities",
        "renamed_usecase_1789928924982.jpg",
        [
            "• Tourist Actor: Ask questions via text/voice, view citation sources, listen to audio answers, explore temple attractions, and view interactive map.",
            "• Admin Actor: Secure login, upload verified temple PDFs, trigger knowledge pipelines, test retrieval diagnostics, and monitor system health.",
            "• Include Relationships: Text/Voice questions automatically include RAG Retrieval and STT transcription.",
            "• Extend Relationships: TTS synthesis executed conditionally on user request."
        ]
    )

    # ==========================================
    # SLIDE 11: ER DIAGRAM (MYSQL 8.0)
    # ==========================================
    add_diagram_slide(
        "GRAPHICAL PORTRAYAL — DATABASE DESIGN",
        "Entity-Relationship (ER) Diagram: MySQL 8.0 Schema",
        "renamed_er_1789928971560.jpg",
        [
            "• admins: Stores admin credentials with Argon2id hashing and 4-tier RBAC roles.",
            "• documents & document_chunks: Stores verified PDFs and ~800-char semantic chunks.",
            "• knowledge_generations: Manages immutable generation versions with active flags.",
            "• embeddings: 1:1 mapping between chunks and ChromaDB 384-dimensional vector IDs.",
            "• chat_sessions & chat_messages: Manages multi-turn conversations and citation JSON."
        ]
    )

    # ==========================================
    # SLIDE 12: HYBRID RAG FLOWCHART
    # ==========================================
    add_diagram_slide(
        "GRAPHICAL PORTRAYAL — RAG PIPELINE",
        "Hybrid RAG Retrieval Flowchart: Query to Grounded Response",
        "renamed_rag_pipeline_1789928491048.jpg",
        [
            "• Language Branching: Kannada queries automatically translated to English via NLLB-200.",
            "• Dual Parallel Retrieval: Dense ChromaDB search + Okapi BM25 keyword matching.",
            "• Reciprocal Rank Fusion: Merges candidates with k=60 to balance semantics and keywords.",
            "• Cross-Encoder Reranking: Neural model selects top-5 most relevant chunks.",
            "• Grounding Guard: If score < -6.0, triggers safe bilingual fallback (zero hallucination)."
        ]
    )

    # ==========================================
    # SLIDE 13: DOCKER DEPLOYMENT ARCHITECTURE
    # ==========================================
    add_diagram_slide(
        "GRAPHICAL PORTRAYAL — DEPLOYMENT ARCHITECTURE",
        "Docker Multi-Container Deployment: 4 Containers & 6 Volumes",
        "renamed_deployment_1789928982009.jpg",
        [
            "• 4 Isolated Containers: Frontend (Nginx SPA, port 80), Backend (FastAPI, port 8000), MySQL 8.0, and Ollama LLM.",
            "• Internal Bridge Network: karnataka-net ensures secure container-to-container communication.",
            "• 6 Persistent Volumes: mysql_data, ollama_data, chroma_data, pdf_storage, piper_models, and huggingface_cache.",
            "• Production Hardened: Multi-stage Dockerfiles with health checks and restart policies."
        ]
    )

    # ==========================================
    # SLIDE 14: KNOWLEDGE GENERATION LIFECYCLE
    # ==========================================
    add_diagram_slide(
        "GRAPHICAL PORTRAYAL — KNOWLEDGE PIPELINE",
        "Knowledge Generation Lifecycle & Document Processing Pipeline",
        "renamed_knowledge_lifecycle_1789931843961.jpg",
        [
            "• PDF Ingestion Flow: Upload -> SHA-256 Check -> PyMuPDF Text Extraction -> Unicode NFC Normalization -> Semantic Chunking -> Vector Embedding -> ChromaDB Indexing -> Validation.",
            "• 8-Stage State Machine: BUILD -> PARSE -> CHUNK -> EMBED -> INDEX -> VALIDATED -> PROMOTE -> ACTIVE.",
            "• Instant Rollback: Immediate pointer-swap restores previous knowledge generation without re-embedding.",
            "• Immutability: Active knowledge is never modified in-place, ensuring reliable tourist queries."
        ]
    )

    # ==========================================
    # SLIDE 15: PROJECT FILE STRUCTURE
    # ==========================================
    add_diagram_slide(
        "GRAPHICAL PORTRAYAL — DIRECTORY STRUCTURE",
        "Project File Structure & Clean Architecture Directory Tree",
        "renamed_file_structure_1789931860782.jpg",
        [
            "• Clean Architecture Separation: backend/ partitioned into api/, application/, domain/ports/, and infrastructure/.",
            "• Domain Ports: Abstract Python ABCs (llm, stt, tts, translation) decouple core logic from third-party libraries.",
            "• Concrete Adapters: Infrastructure layer provides Ollama, Whisper, NLLB-200, and Piper implementations.",
            "• Frontend Modularization: Reusable React 19 components for chat, voice, citations, map, and admin pages."
        ],
        is_portrait=True
    )

    # ==========================================
    # SLIDE 16: CONCLUSION & FUTURE SCOPE
    # ==========================================
    s16 = prs.slides.add_slide(blank_layout)
    add_header(s16, "SUMMARY & LOOKING AHEAD", "Conclusion & Future Scope")

    cards_c_f = [
        ("Project Conclusion",
         ["• Successfully developed a 100% software-based, locally deployable AI tourist guide platform dedicated to Beluru Chennakeshava Temple.",
          "• Hybrid RAG architecture (dense vector + BM25 + Cross-Encoder) achieves 100% grounding accuracy and completely eliminates hallucinations.",
          "• Provides zero-login bilingual (English & Kannada) text and voice interaction with server-authoritative citations.",
          "• Fully offline standalone operation ensures privacy, zero ongoing cloud API costs, and reliability at heritage sites."]),
        ("Future Scope & Roadmap",
         ["• Conversational Voice Latency Optimization: Transition to streaming chunk-based processing and GPU acceleration for real-time speech turnaround.",
          "• Expanded Architectural Knowledge: Ingest detailed temple blueprints, stone inscriptions (Shasana), and high-resolution sculpture archives.",
          "• Additional Indian Languages: Extend NLLB translation pairs to support Hindi, Tamil, Telugu, and Marathi.",
          "• Mobile Progressive Web App (PWA): Enable offline on-device client caching and tour guides directly in tourist mobile browsers.",
          "• AR Sculpture Identification: Camera-based visual recognition of the 42 Madanika bracket figures with instant AI narration."])
    ]

    for i, (title, bullets) in enumerate(cards_c_f):
        cx = Inches(0.8 + i * 5.95)
        card = s16.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, cx, Inches(1.65), Inches(5.75), Inches(5.2))
        card.fill.solid()
        card.fill.fore_color.rgb = COLOR_CARD_BG
        card.line.color.rgb = COLOR_CARD_BORDER

        ctf = card.text_frame
        ctf.word_wrap = True
        ctf.margin_left = ctf.margin_right = Inches(0.28)
        ctf.margin_top = Inches(0.25)

        cp0 = ctf.paragraphs[0]
        cp0.text = title
        cp0.font.size = Pt(14)
        cp0.font.bold = True
        cp0.font.color.rgb = COLOR_HEADER_BLUE

        for b in bullets:
            bp = ctf.add_paragraph()
            bp.text = b
            bp.font.size = Pt(11)
            bp.font.color.rgb = COLOR_TEXT_MAIN
            bp.space_before = Pt(8)

    # ==========================================
    # SLIDE 17: REFERENCES
    # ==========================================
    s17 = prs.slides.add_slide(blank_layout)
    add_header(s17, "ACADEMIC & TECHNICAL SOURCES", "References & Documentation")

    refs = [
        ("1. FastAPI Web Framework", "Sebastián Ramírez, 'FastAPI: Modern, High-Performance Web Framework for Python 3.10+', 2024. https://fastapi.tiangolo.com/"),
        ("2. Sentence-BERT Embeddings", "Nils Reimers and Iryna Gurevych, 'Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks', Proceedings of EMNLP 2019."),
        ("3. Cross-Encoder Reranking", "MS MARCO Passage Ranking with MiniLM Cross-Encoders, Hugging Face, 2021. https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-6-v2"),
        ("4. ChromaDB Vector Store", "Jeff Huber and Anton Troynikov, 'Chroma: The AI-Native Open-Source Embedding Database', 2023. https://www.trychroma.com/"),
        ("5. Ollama & Phi-3 Mini", "Microsoft Research, 'Phi-3 Technical Report: A Highly Capable Language Model Locally on Your Phone', arXiv:2404.14219, 2024."),
        ("6. Meta NLLB-200 Translation", "NLLB Team, Meta AI, 'No Language Left Behind: Scaling Human-Centered Machine Translation', arXiv:2207.04672, 2022."),
        ("7. Faster-Whisper ASR", "Guillaume Klein et al., 'Faster-Whisper: High-Performance Speech Recognition with CTranslate2', SYSTRAN, 2023."),
        ("8. Piper Neural TTS", "Michael Hansen, 'Piper: Fast, Local Neural Text-to-Speech System Using ONNX', Rhasspy, 2023. https://github.com/rhasspy/piper"),
        ("9. Meta MMS Multilingual Speech", "Vineel Pratap et al., 'Scaling Speech Technology to 1,000+ Languages', Meta AI Research, 2023."),
        ("10. Beluru Chennakeshava Documentation", "Archaeological Survey of India (ASI) & Karnataka State Tourism Development Corporation (KSTDC) Official Heritage Records.")
    ]

    for i, (rtitle, rdesc) in enumerate(refs):
        col = i % 2
        row = i // 2
        cx = Inches(0.8 + col * 5.95)
        cy = Inches(1.65 + row * 1.0)

        rcard = s17.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, cx, cy, Inches(5.75), Inches(0.88))
        rcard.fill.solid()
        rcard.fill.fore_color.rgb = COLOR_CARD_BG
        rcard.line.color.rgb = COLOR_CARD_BORDER

        rtf = rcard.text_frame
        rtf.word_wrap = True
        rtf.margin_left = rtf.margin_right = Inches(0.2)
        rtf.margin_top = Inches(0.1)

        rp0 = rtf.paragraphs[0]
        rp0.text = rtitle
        rp0.font.size = Pt(11)
        rp0.font.bold = True
        rp0.font.color.rgb = COLOR_HEADER_BLUE

        rp1 = rtf.add_paragraph()
        rp1.text = rdesc
        rp1.font.size = Pt(9.5)
        rp1.font.color.rgb = COLOR_TEXT_MAIN
        rp1.space_before = Pt(2)

    prs.save(OUTPUT_PPTX_PATH)
    print(f"SUCCESS: Presentation saved to {OUTPUT_PPTX_PATH}")

if __name__ == "__main__":
    create_deck()
