"""
Build and promote expanded authentic Karnataka heritage tourism corpus.
Documents created:
1. Pattadakal_UNESCO_Guide.pdf (2 pages)
2. Badami_Caves_Guide.pdf (3 pages)
3. Aihole_Heritage_Guide.pdf (2 pages)
4. Hampi_Vijayanagara_Guide.pdf (2 pages)
5. Belur_Halebidu_Hoysala_Guide.pdf (3 pages)
Total: 5 documents, 12 pages.
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timezone
import pymupdf as fitz
from sqlalchemy import select
from app.infrastructure.db.session import get_session_factory
from app.infrastructure.db.models.admin import Admin, AdminRole
from app.infrastructure.db.models.document import Document
from app.application.documents.service import upload_document
from app.application.knowledge.service import KnowledgeService
from app.core.security import hash_password


class MockUploadFile:
    def __init__(self, filename: str, content: bytes, content_type: str = "application/pdf"):
        self.filename = filename
        self._content = content
        self.content_type = content_type

    async def read(self) -> bytes:
        return self._content


def _create_pattadakal_pdf() -> bytes:
    doc = fitz.open()
    
    # Page 1
    p1 = doc.new_page()
    rect1 = fitz.Rect(50, 50, 550, 750)
    text1 = (
        "PATTADAKAL UNESCO WORLD HERITAGE SITE (ಪಟ್ಟದಕಲ್ಲು)\n\n"
        "OVERVIEW AND HISTORICAL CONTEXT\n"
        "Pattadakal, also known as Raktapura or Pattada Kisuvolal, is a historic complex of 7th and 8th century CE Hindu and Jain temples located in northern Karnataka. Situated on the west bank of the sacred Malaprabha River in Bagalkot district, it was the principal coronation site (Pattadakallu) for kings of the Early Chalukya dynasty of Badami.\n\n"
        "ARCHITECTURAL SIGNIFICANCE\n"
        "Pattadakal represents the pinnacle of early South Indian temple development and is globally renowned for illustrating the harmonious confluence of northern Nagara (Rekha-Nagara) and southern Dravida architectural traditions. The monuments were designated a UNESCO World Heritage Site in 1987. The temples feature magnificent red-golden sandstone sourced from nearby Malaprabha valley quarries."
    )
    p1.insert_textbox(rect1, text1, fontsize=11)

    # Page 2
    p2 = doc.new_page()
    rect2 = fitz.Rect(50, 50, 550, 750)
    text2 = (
        "KEY TEMPLES AND MONUMENTS AT PATTADAKAL\n\n"
        "1. Virupaksha Temple (Lokeshwara):\n"
        "The grandest temple at Pattadakal, commissioned around 740 CE by Queen Lokamahadevi to celebrate her husband King Vikramaditya II's victory over the Pallavas of Kanchipuram. Built in sophisticated Dravida style with an imposing vimana, massive monolithic Nandi pavilion, and black stone Shiva Linga in the inner sanctum. The perimeter walls display intricate relief friezes of the Ramayana and Mahabharata.\n\n"
        "2. Mallikarjuna Temple (Trailokyeshwara):\n"
        "Built concurrently by Vikramaditya II's second queen, Trailokyamahadevi, to celebrate the same Kanchi military campaign. It mirrors the Dravida plan of Virupaksha on a slightly smaller scale.\n\n"
        "3. Sangameshwara Temple:\n"
        "The oldest surviving temple at the site, commissioned by King Vijayaditya (696–733 CE). Designed in classical early Dravida style with serene simplicity.\n\n"
        "4. Papanatha Temple:\n"
        "A 740 CE temple showcasing northern Nagara architecture with a curvilinear shikhara, decorative gavaksha arches, and detailed Ramayana narratives along its outer plinth.\n\n"
        "5. Jain Narayana Temple:\n"
        "A 9th-century CE temple from the Rashtrakuta period featuring a three-tiered Dravida vimana and large stone elephant sculptures flanking the mukhamandapa."
    )
    p2.insert_textbox(rect2, text2, fontsize=11)

    b = doc.tobytes()
    doc.close()
    return b


def _create_badami_pdf() -> bytes:
    doc = fitz.open()

    # Page 1
    p1 = doc.new_page()
    rect1 = fitz.Rect(50, 50, 550, 750)
    text1 = (
        "BADAMI ROCK-CUT CAVE TEMPLES (ಬಾದಾಮಿ)\n\n"
        "HISTORICAL CAPITAL OF THE CHALUKYAS\n"
        "Badami, originally known as Vatapi, was the regal capital of the Early Chalukya dynasty from 540 to 757 CE, established by King Pulakeshin I. Nestled in a rugged sandstone ravine in Bagalkot district, the settlement developed around the artificial Agastya Tirtha water reservoir, flanked by towering red sandstone cliffs.\n\n"
        "THE FOUR MONUMENTAL ROCK-CUT CAVES\n"
        "The rock-cut temples are carved horizontally into the steep cliff face, arranged chronologically from Cave 1 at the lowest level to Cave 4 at the highest elevation. Each cave comprises an entrance verandah (mukhamandapa), a columned main hall (mahamandapa), and a small square sanctum (garbhagriha) hollowed deep into the living rock."
    )
    p1.insert_textbox(rect1, text1, fontsize=11)

    # Page 2
    p2 = doc.new_page()
    rect2 = fitz.Rect(50, 50, 550, 750)
    text2 = (
        "DETAILED DESCRIPTIONS OF BADAMI CAVES\n\n"
        "Cave 1 (Shaivism):\n"
        "Dedicated to Lord Shiva, carved around 550 CE. Features the iconic 18-armed dancing Nataraja relief portraying 81 distinct mudras and postures of classical dance. Also contains monumental reliefs of Harihara (half Shiva, half Vishnu) and Ardhanarishvara (half Shiva, half Parvati).\n\n"
        "Cave 2 (Vaishnavism):\n"
        "Dedicated to Lord Vishnu, reached by a flight of 64 steps from Cave 1. Noted for colossal ceiling carvings and relief panels of Vishnu in his cosmic avatar Trivikrama (Vamana) with one foot planted on Earth and another raised to the heavens, as well as the boar avatar Varaha rescuing Bhudevi.\n\n"
        "Cave 3 (Maha-Vishnu):\n"
        "The largest and most elaborately carved cave, bearing a crucial Sanskrit foundation inscription dated to Saka 500 (578 CE) during the reign of King Kirtivarman I by his brother King Mangalesha. Famous for the magnificent 8-armed seated Vishnu on the coiled serpent Shesha (Anantasayana) and the fearsome seated Narasimha."
    )
    p2.insert_textbox(rect2, text2, fontsize=11)

    # Page 3
    p3 = doc.new_page()
    rect3 = fitz.Rect(50, 50, 550, 750)
    text3 = (
        "JAIN CAVE AND LAKESIDE MONUMENTS\n\n"
        "Cave 4 (Jainism):\n"
        "Carved in the late 6th to early 7th century CE, dedicated to Jain Tirthankaras. The sanctum holds a serene sculpture of Lord Mahavira seated on a lion throne (Simhasana). The verandah walls feature Parshvanatha sheltered by a multi-hooded cobra and Bahubali (Gommata) standing in deep kayotsarga meditation with creepers climbing his legs.\n\n"
        "BHUTANATHA TEMPLE COMPLEX\n"
        "Located on the eastern edge of Agastya Lake, the Bhutanatha group of sandstone temples dates from the 7th to 11th centuries. Built in early Dravida style, its open mandapa extends directly into the tranquil lake waters, creating one of Karnataka's most famous heritage vistas."
    )
    p3.insert_textbox(rect3, text3, fontsize=11)

    b = doc.tobytes()
    doc.close()
    return b


def _create_aihole_pdf() -> bytes:
    doc = fitz.open()

    # Page 1
    p1 = doc.new_page()
    rect1 = fitz.Rect(50, 50, 550, 750)
    text1 = (
        "AIHOLE: CRADLE OF INDIAN TEMPLE ARCHITECTURE (ಐಹೊಳೆ)\n\n"
        "ARCHAEOLOGICAL AND ARCHITECTURAL HERITAGE\n"
        "Aihole, anciently called Aryapura, is a historic temple village on the Malaprabha River in Bagalkot district. Known as the laboratory and cradle of Hindu and Jain rock-cut and structural temple architecture, Aihole contains over 120 stone temples dating between the 5th and 12th centuries CE built by Chalukya master craftsmen.\n\n"
        "THE FAMOUS DURGA TEMPLE\n"
        "The Durga Temple (built late 7th to early 8th century CE) is Aihole's architectural centerpiece. Named after the surrounding Durg (protective fort rampart), it is celebrated for its unique apsidal (horseshoe-shaped or gajaprishta) plan resembling early Buddhist chaitya halls. It features a peripteral colonnaded corridor with masterfully sculpted bracket panels of Mahishasuramardini, Varaha, and Shiva with Nandi."
    )
    p1.insert_textbox(rect1, text1, fontsize=11)

    # Page 2
    p2 = doc.new_page()
    rect2 = fitz.Rect(50, 50, 550, 750)
    text2 = (
        "LAD KHAN, RAVANA PHADI, AND MEGUTI INSCRIPTION\n\n"
        "Lad Khan Temple:\n"
        "A 5th-6th century CE temple originally serving as a royal assembly hall before being converted into a Shiva shrine. Features a square cave-like pillared hall, sloped stone roof slabs with timber-imitation joinery, and exquisite floral lattice stone windows.\n\n"
        "Ravana Phadi Cave:\n"
        "A 6th-century rock-cut Shaivite cave sanctuary featuring a majestic ten-armed dancing Shiva Nataraja accompanied by Ganesha, Kartikeya, and the Saptamatrikas (Seven Mother Goddesses).\n\n"
        "Meguti Hill Jain Temple & The Aihole Inscription (634 CE):\n"
        "Constructed atop Meguti Hill in 634 CE by the royal court poet Ravikirti during the reign of Chalukya Emperor Pulakeshin II. The temple wall bears the famous Aihole Sanskrit Inscription written in early Old Kannada-Telugu script, describing Pulakeshin II's military conquests and his historic victory over Emperor Harsha of Kannauj on the banks of the Narmada River."
    )
    p2.insert_textbox(rect2, text2, fontsize=11)

    b = doc.tobytes()
    doc.close()
    return b


def _create_hampi_pdf() -> bytes:
    doc = fitz.open()

    # Page 1
    p1 = doc.new_page()
    rect1 = fitz.Rect(50, 50, 550, 750)
    text1 = (
        "HAMPI: CAPITAL OF THE VIJAYANAGARA EMPIRE (ಹಂಪಿ)\n\n"
        "HISTORICAL SPLENDOR ON THE TUNGABHADRA\n"
        "Hampi, designated a UNESCO World Heritage Site in 1986, was the imperial capital of the Vijayanagara Empire from 1336 to 1565 CE. Founded by the Sangama brothers Harihara I and Bukka Raya I along the banks of the Tungabhadra River in Vijayanagara district (formerly Bellary), Hampi grew into one of the largest and wealthiest metropolises in the medieval world.\n\n"
        "THE REIGN OF EMPEROR KRISHNADEVARAYA\n"
        "The empire attained its cultural and political golden age under Emperor Krishnadevaraya of the Tuluva dynasty (reigned 1509–1529 CE), a visionary patron of arts, literature, and monumental temple construction. The rugged boulder-strewn landscape features over 1,600 surviving monuments across 41 square kilometers."
    )
    p1.insert_textbox(rect1, text1, fontsize=11)

    # Page 2
    p2 = doc.new_page()
    rect2 = fitz.Rect(50, 50, 550, 750)
    text2 = (
        "KEY MONUMENTS OF HAMPI\n\n"
        "1. Virupaksha Temple Complex:\n"
        "The primary and continuously functioning pilgrimage center dedicated to Lord Shiva (Virupaksha/Pampa). Features a towering 50-meter eastern gopuram, extensive pillared halls, and ceiling murals from the 16th century.\n\n"
        "2. Vijaya Vittala Temple & Stone Chariot:\n"
        "The crowning achievement of Vijayanagara architecture, dedicated to Lord Vishnu. Renowned for the iconic monolithic Stone Chariot (Garuda shrine) featured on the Indian 50-rupee currency note. The grand Ranga Mandapa contains 56 monolithic musical pillars (sa-re-ga-ma pillars) carved with resonant stone shafts.\n\n"
        "3. Royal Enclosure & Secular Architecture:\n"
        "The administrative core containing the stepped tank (Pushkarani), Mahanavami Dibba platform used for state festivals, the Queen's Bath, the two-storeyed Lotus Mahal with elegant arched cusps in Indo-Islamic style, and the massive eleven-chambered Elephant Stables."
    )
    p2.insert_textbox(rect2, text2, fontsize=11)

    b = doc.tobytes()
    doc.close()
    return b


def _create_hoysala_pdf() -> bytes:
    doc = fitz.open()

    # Page 1
    p1 = doc.new_page()
    rect1 = fitz.Rect(50, 50, 550, 750)
    text1 = (
        "BELUR AND HALEBIDU: SACRED ENSEMBLES OF THE HOYSALAS (ಬೇಲೂರು - ಹಳೇಬೀಡು)\n\n"
        "HOYSALA DYNASTY AND UNESCO RECOGNITION\n"
        "The Hoysala Empire ruled over Karnataka from the 10th to 14th centuries CE, establishing their principal capitals at Belur (Velapuri) and Halebidu (Dorasamudra) in Hassan district. In September 2023, the 'Sacred Ensembles of the Hoysalas' were inscribed as a UNESCO World Heritage Site in recognition of their unsurpassed sculptural virtuosity, intricate micro-carvings, and unique stellate temple architecture.\n\n"
        "ARCHITECTURAL CHARACTERISTICS\n"
        "Hoysala temples are constructed from soft chloritic schist (soapstone) that hardens upon atmospheric exposure, permitting jewel-like ornamental detail. Temples stand on elevated star-shaped platforms (jagati) providing an open circumambulatory path (pradakshinapatha) around the perimeter."
    )
    p1.insert_textbox(rect1, text1, fontsize=11)

    # Page 2
    p2 = doc.new_page()
    rect2 = fitz.Rect(50, 50, 550, 750)
    text2 = (
        "BELUR CHENNAKESHAVA TEMPLE COMPLEX\n\n"
        "COMMISSIONING AND DEDICATION\n"
        "The Chennakeshava Temple at Belur was commissioned in 1117 CE by King Vishnuvardhana (formerly Bittideva) to celebrate his military triumph over the Chola Viceroy of Talakadu at the historic Battle of Talakadu and his conversion from Jainism to Vaishnavism under the guidance of saint Ramanujacharya.\n\n"
        "MADANIKAS (BRACKET FIGURES)\n"
        "The exterior pillars feature 42 celebrated bracket figures (Madanikas or Salabhanjikas) representing feminine beauty, music, and dance. The most famous is 'Darpana Sundari' (the beauty admiring herself in a mirror), alongside the Huntress, the Drummer, and the Lady with a Parrot. The inner navaranga hall contains polished lathed pillars of black soapstone, notably the Mohini pillar and the intricately carved Narasimha pillar."
    )
    p2.insert_textbox(rect2, text2, fontsize=11)

    # Page 3
    p3 = doc.new_page()
    rect3 = fitz.Rect(50, 50, 550, 750)
    text3 = (
        "HALEBIDU HOYSALESWARA TEMPLE\n\n"
        "TWIN TEMPLE ARCHITECTURE\n"
        "Commissioned around 1121 CE by King Vishnuvardhana and wealthy merchant Ketamalla, the Hoysaleswara Temple is a monumental twin-shrine (dvikuta) complex dedicated to Hoysaleswara and Shantaleswara (named after Queen Shantala Devi). Designed by master architect Kedaroja.\n\n"
        "WALL FRIEZES AND NARRATIVE RELIEFS\n"
        "The exterior base features eight continuous horizontal tiers of relief friezes: the lowest layer with 1,248 charging war elephants, followed by lions, floral scrolls, cavalry horses, narrative friezes, makaras (mythical sea creatures), and hamsas (sacred swans). The upper walls display over 240 colossal sculptures of Hindu deities, including Lord Shiva as Gajasurasamhara dancing on the slain elephant demon, Vishnu, Brahma, Saraswati, and Ravana lifting Mount Kailash."
    )
    p3.insert_textbox(rect3, text3, fontsize=11)

    b = doc.tobytes()
    doc.close()
    return b


async def main():
    session_factory = get_session_factory()
    async with session_factory() as session:
        # Step 1: Fetch super admin
        admin_stmt = select(Admin).where(Admin.username == "admin")
        admin = (await session.execute(admin_stmt)).scalar_one_or_none()
        if not admin:
            admin = Admin(
                username="admin",
                email="admin@karnataka.gov.in",
                hashed_password=hash_password("Admin@Karnataka2026"),
                role=AdminRole.SUPER_ADMIN,
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )
            session.add(admin)
            await session.commit()

        # Step 2: Upload all 5 documents
        docs_to_upload = [
            ("Pattadakal_UNESCO_Guide.pdf", _create_pattadakal_pdf()),
            ("Badami_Caves_Guide.pdf", _create_badami_pdf()),
            ("Aihole_Heritage_Guide.pdf", _create_aihole_pdf()),
            ("Hampi_Vijayanagara_Guide.pdf", _create_hampi_pdf()),
            ("Belur_Halebidu_Hoysala_Guide.pdf", _create_hoysala_pdf()),
        ]

        doc_ids = []
        for fn, b in docs_to_upload:
            mock_file = MockUploadFile(fn, b)
            try:
                doc = await upload_document(session=session, file=mock_file, current_admin=admin)
                print(f"Uploaded {fn} -> ID: {doc.id}")
                doc_ids.append(doc.id)
            except Exception as e:
                # If duplicate already exists, lookup its ID
                print(f"Document {fn} upload error or exists ({e}), looking up existing record...")
                import hashlib
                sha = hashlib.sha256(b).hexdigest()
                existing = (await session.execute(select(Document).where(Document.sha256_hash == sha))).scalar_one_or_none()
                if existing:
                    print(f"Using existing {fn} -> ID: {existing.id}")
                    doc_ids.append(existing.id)
                else:
                    raise e

        # Step 3: Build Generation
        print(f"\nBuilding new Knowledge Generation from {len(doc_ids)} documents...")
        know_svc = KnowledgeService(session)
        gen = await know_svc.build_generation(
            admin_id=admin.id,
            document_ids=doc_ids,
            description="Comprehensive Karnataka UNESCO & State Heritage Corpus (Pattadakal, Badami, Aihole, Hampi, Belur, Halebidu)",
        )
        print(f"Built Generation ID: {gen.id} (Version: {gen.generation_version}, Status: {gen.status}, Chunks: {gen.chunk_count})")

        # Step 4: Promote Generation to ACTIVE
        print(f"\nPromoting Generation {gen.id} to ACTIVE...")
        promoted = await know_svc.promote_generation(gen.id, admin.id)
        print(f"Generation {promoted.id} is now ACTIVE={promoted.is_active} (Status: {promoted.status})")


if __name__ == "__main__":
    asyncio.run(main())
