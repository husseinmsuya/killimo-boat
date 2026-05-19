"""
rag/rag_system.py
-----------------
RAG system ya Kilimo Bot — documents za mazao YOTE ya Tanzania.

Vyanzo vya kweli (bure, kuthibitishwa na wataalamu):
  - IITA/TARI/USAID  : Mahindi
  - FAO              : Mpunga, Nyanya, Mihogo, Kilimo Tanzania
  - TARI             : Maharagwe
  - CIMMYT           : Magonjwa ya Mahindi
  - WorldVeg         : Nyanya

Mazao yanayofunikwa:
  mahindi, mpunga, mihogo, maharagwe, nyanya, mifugo

Maboresho ya v4:
  - Toa tz_agriculture_annual_2024 (ilikuwa na majedwali yasiyofaa)
  - Chunking kwa sentensi kamili — si maneno tu
  - Chuja jedwali na nambari kutoka chunks
  - Ongeza documents za magonjwa ya mahindi na nyanya
"""

import os
import sys
import argparse
import requests
import re
import chromadb
from chromadb.utils import embedding_functions
import fitz  # PyMuPDF

# ── Vyanzo vya documents ──────────────────────────────────────
DOCUMENTS = [

    # ── MAHINDI ──────────────────────────────────────────────
    {
        "id": "maize_manual_tz",
        "title": "Maize Production Manual for Smallholder Farmers in Tanzania",
        "source": "IITA / TARI / USAID Feed the Future",
        "url": "https://cgspace.cgiar.org/server/api/core/bitstreams/a5a24307-e6c2-40cd-9138-493f8ff0e94a/content",
        "topics": ["mahindi", "maize", "mbolea", "wadudu", "fall army worm", "kupanda", "mavuno"],
    },
    {
        "id": "maize_value_chain_tz",
        "title": "The Maize Value Chain in Tanzania - FAO Southern Highlands",
        "source": "FAO Tanzania",
        "url": "https://www.fao.org/fileadmin/user_upload/ivc/PDF/SFVC/Tanzania_maize.pdf",
        "topics": ["mahindi", "soko", "bei", "value chain", "wakulima wadogo"],
    },
    {
        "id": "maize_diseases_africa",
        "title": "Maize Diseases and Pests in Africa - CIMMYT",
        "source": "CIMMYT",
        "url": "https://repository.cimmyt.org/bitstream/handle/10883/1262/9031.pdf",
        "topics": ["mahindi", "maize", "magonjwa", "wadudu", "madoa", "rust", "blight", "FAW", "stem borer"],
    },

    # ── MPUNGA ───────────────────────────────────────────────
    {
        "id": "rice_value_chain_tz",
        "title": "The Rice Value Chain in Tanzania - FAO Southern Highlands",
        "source": "FAO Tanzania",
        "url": "https://www.fao.org/fileadmin/user_upload/ivc/PDF/SFVC/Tanzania_rice.pdf",
        "topics": ["mpunga", "rice", "umwagiliaji", "paddy", "soko", "msimu", "kupanda"],
    },

    # ── MAHARAGWE (BEANS) ─────────────────────────────────────
    {
        "id": "beans_variety_catalogue_tari",
        "title": "Variety Catalogue of Common Beans in Tanzania - TARI",
        "source": "Tanzania Agricultural Research Institute (TARI)",
        "url": "https://www.tari.go.tz/assets/uploads/documents/ea8db0325b3534ca3fec5354ea51d255.pdf",
        "topics": ["maharagwe", "beans", "aina za maharagwe", "mbegu", "TARI", "varieties"],
    },

    # ── NYANYA (TOMATO) ───────────────────────────────────────
    {
        "id": "tomato_ipm_fao",
        "title": "Tomato Integrated Pest Management - FAO Ecological Guide",
        "source": "FAO / CABI",
        "url": "https://openknowledge.fao.org/server/api/core/bitstreams/79f188d5-64cf-49a0-b924-47bc7a184eb5/content",
        "topics": ["nyanya", "tomato", "wadudu", "magonjwa", "IPM", "mboga", "tuta absoluta"],
    },

    # ── MIHOGO (CASSAVA) ──────────────────────────────────────
    {
        "id": "cassava_africa_fao",
        "title": "A Review of Cassava in Africa - Tanzania Case Study",
        "source": "FAO",
        "url": "https://www.fao.org/4/a0154e/a0154e09.htm",
        "topics": ["mihogo", "cassava", "mbegu", "wadudu", "kupanda", "mavuno", "CMD", "CBSD"],
    },

    # ── KILIMO KWA UJUMLA - TANZANIA ──────────────────────────
    {
        "id": "tz_climate_smart_agriculture",
        "title": "Tanzania Climate Smart Agriculture Programme 2015-2025",
        "source": "FAO / Serikali ya Tanzania",
        "url": "https://faolex.fao.org/docs/pdf/tan215306.pdf",
        "topics": ["hali ya hewa", "climate", "kilimo", "mvua", "ukame", "misimu", "Tanzania"],
    },
    {
        "id": "fao_tz_country_crops",
        "title": "Tanzania Country Report - FAO Plant Genetic Resources",
        "source": "FAO",
        "url": "https://www.fao.org/fileadmin/templates/agphome/documents/PGR/SoW1/africa/TANZANIA.pdf",
        "topics": ["mazao", "mbegu", "aina za mazao", "Tanzania", "rice", "beans", "cassava", "genetic"],
    },

    # ── MIFUGO (LIVESTOCK) ────────────────────────────────────
    {
        "id": "livestock_tz_bioenergy",
        "title": "Tanzania Bioenergy and Food Security - FAO (includes livestock data)",
        "source": "FAO",
        "url": "https://www.fao.org/4/aq179e/aq179e.pdf",
        "topics": ["mifugo", "ng'ombe", "kuku", "kilimo", "chakula", "Tanzania", "livestock"],
    },
]

# ── ChromaDB setup ─────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "chromadb")
COLLECTION_NAME = "kilimo_tz_v4"  # v4 — database safi bila annual report
EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

def get_collection():
    client = chromadb.PersistentClient(path=DB_PATH)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBED_MODEL
    )
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"}
    )

# ── Pakua PDF ─────────────────────────────────────────────────
def download_pdf(url, save_path):
    if os.path.exists(save_path):
        print(f"  [cache] {os.path.basename(save_path)}")
        return True
    try:
        print(f"  [download] {url[:65]}...")
        r = requests.get(
            url, timeout=30, stream=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; KilimoBot/1.0)"}
        )
        r.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        size_kb = os.path.getsize(save_path) // 1024
        print(f"  [ok] {size_kb} KB")
        return True
    except Exception as e:
        print(f"  [fail] {e}")
        return False

def fetch_html_text(url):
    """Kwa vyanzo vya HTML (si PDF) kama FAO htm pages."""
    try:
        r = requests.get(
            url, timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (compatible; KilimoBot/1.0)"}
        )
        r.raise_for_status()
        text = re.sub(r'<[^>]+>', ' ', r.text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    except Exception as e:
        print(f"  [fail] HTML fetch: {e}")
        return ""

def extract_pdf_text(pdf_path):
    """Toa maandishi yote kutoka PDF kwa PyMuPDF."""
    try:
        doc = fitz.open(pdf_path)
        text = "".join(page.get_text() for page in doc)
        doc.close()
        return text
    except Exception as e:
        print(f"  [fail] PDF read: {e}")
        return ""

# ── Gawanya maandishi kwa vipande ─────────────────────────────
def chunk_text(text, chunk_size=300, overlap=30):
    """
    Gawanya kwa sentensi kamili — chunk ndogo = matokeo sahihi zaidi.

    Maboresho ya v4:
    - Gawanya kwa sentensi (si maneno tu)
    - Chuja jedwali: sentensi zenye alpha ratio chini ya 40% zinaachwa
    - Chuja sentensi fupi (chini ya maneno 6)
    - Overlap kwa sentensi 2 za mwisho (si maneno)
    """
    # Safisha kwanza
    text = re.sub(r'\s+', ' ', text).strip()

    # Gawanya kwa sentensi
    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []
    current = []
    current_len = 0

    for sent in sentences:
        words = sent.split()

        # Ruka sentensi fupi sana — hazina maana
        if len(words) < 6:
            continue

        # Ruka jedwali na nambari — alpha ratio chini ya 40%
        alpha_ratio = sum(c.isalpha() for c in sent) / max(len(sent), 1)
        if alpha_ratio < 0.4:
            continue

        # Ruka sentensi zenye maneno mengi ya nambari/msimbo
        number_words = sum(1 for w in words if re.match(r'^\d+[\d/\-\.]*$', w))
        if number_words > len(words) * 0.5:
            continue

        # Ikiwa chunk imejaa — hifadhi na anza mpya
        if current_len + len(words) > chunk_size and current:
            chunk_str = ' '.join(current)
            if len(chunk_str.split()) >= 30:
                chunks.append(chunk_str)
            # Overlap — chukua sentensi 2 za mwisho kwa muktadha
            current = current[-2:] if len(current) >= 2 else current[:]
            current_len = sum(len(s.split()) for s in current)

        current.append(sent)
        current_len += len(words)

    # Ongeza kipande cha mwisho
    if current:
        chunk_str = ' '.join(current)
        if len(chunk_str.split()) >= 30:
            chunks.append(chunk_str)

    return chunks

# ── Jenga database ────────────────────────────────────────────
def build_database():
    print("\n🌾 Kujenga RAG Database ya Kilimo Bot v4")
    print("=" * 60)
    print(f"Documents: {len(DOCUMENTS)}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Mazao: Mahindi, Mpunga, Maharagwe, Nyanya, Mihogo, Mifugo\n")

    pdf_dir = os.path.join(os.path.dirname(__file__), "..", "data", "pdfs")
    os.makedirs(pdf_dir, exist_ok=True)

    collection = get_collection()

    # Angalia kama database ina data tayari
    if collection.count() > 0:
        print(f"⚠️  Database ina chunks {collection.count()} tayari.")
        ans = input("Jenga upya? (y/n): ").strip().lower()
        if ans != 'y':
            print("Imebaki bila mabadiliko.")
            return
        # Futa zote
        collection.delete(where={"doc_id": {"$ne": ""}})
        print("  [ok] Database imefutwa — inajenga upya...\n")

    total_chunks = 0
    skipped = 0

    for doc in DOCUMENTS:
        print(f"📄 {doc['title'][:58]}...")
        print(f"   Chanzo: {doc['source']}")

        # Angalia kama ni HTML au PDF
        is_html = not doc["url"].endswith(".pdf") and "htm" in doc["url"]

        if is_html:
            print(f"  [html] Inasoma ukurasa wa HTML...")
            text = fetch_html_text(doc["url"])
        else:
            pdf_path = os.path.join(pdf_dir, f"{doc['id']}.pdf")
            ok = download_pdf(doc["url"], pdf_path)
            text = extract_pdf_text(pdf_path) if ok else ""

        # Angalia maandishi yaliyopatikana
        if not text or len(text.split()) < 100:
            print(f"  ⚠️  Imeachwa — maandishi mafupi sana au hayakupatikana\n")
            skipped += 1
            continue

        word_count = len(text.split())
        print(f"  Maneno: {word_count:,}")

        # Gawanya kwa vipande
        chunks = chunk_text(text)
        print(f"  Vipande (baada ya kuchuja jedwali): {len(chunks)}")

        if len(chunks) == 0:
            print(f"  ⚠️  Hakuna chunks zilizopita kichujio — imeachwa\n")
            skipped += 1
            continue

        # Hifadhi ChromaDB kwa batch
        batch_size = 50
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i: i + batch_size]
            collection.add(
                documents=batch,
                ids=[f"{doc['id']}_{i + j}" for j in range(len(batch))],
                metadatas=[{
                    "doc_id":       doc["id"],
                    "title":        doc["title"],
                    "source":       doc["source"],
                    "topics":       ", ".join(doc["topics"]),
                    "chunk_index":  i + j,
                } for j in range(len(batch))]
            )

        total_chunks += len(chunks)
        print(f"  ✅ Imehifadhiwa vizuri\n")

    print("=" * 60)
    print(f"✅ Database imekamilika!")
    print(f"   Documents: {len(DOCUMENTS) - skipped}/{len(DOCUMENTS)}")
    print(f"   Chunks zote: {total_chunks:,}")
    print(f"\n   Mazao yanayofunikwa:")
    print(f"   🌽 Mahindi   🌾 Mpunga    🫘 Maharagwe")
    print(f"   🍅 Nyanya    🥔 Mihogo    🐄 Mifugo")
    print(f"   ☀️  Hali ya hewa          📊 Masoko")
    print(f"\n   Sasa anzisha server: python app.py")

# ── Tafuta (Search) ───────────────────────────────────────────
def search(query, n_results=4):
    """
    Tafuta chunks zinazofanana na swali.
    Inarudisha list ya dicts: [{text, title, source, score}]
    Score threshold: 0.30 (cosine similarity)
    """
    try:
        collection = get_collection()
        if collection.count() == 0:
            print("[rag] ⚠️  Database tupu — jenga kwanza: python rag/rag_system.py --build")
            return []

        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        output = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # Badilisha cosine distance → similarity score
            score = 1 - (dist / 2)
            if score > 0.30:  # Chukua results zinazofaa tu
                output.append({
                    "text":   doc,
                    "title":  meta.get("title", ""),
                    "source": meta.get("source", ""),
                    "topics": meta.get("topics", ""),
                    "score":  round(score, 3),
                })

        return output

    except Exception as e:
        print(f"[rag] Search error: {e}")
        return []

def format_context(results):
    """Tengeneza context string kutoka search results — itumike kwenye prompt."""
    if not results:
        return ""
    parts = []
    for r in results:
        parts.append(
            f"--- Chanzo: {r['title']} ({r['source']}) ---\n{r['text']}"
        )
    return "\n\n".join(parts)

# ── Test ──────────────────────────────────────────────────────
def test_search():
    """Jaribu mfumo wa kutafuta kwa maswali ya kawaida."""
    queries = [
        "mahindi yana madoa meupe ni ugonjwa gani",
        "nyanya magonjwa ya ukungu jinsi ya kutibu",
        "mpunga kupanda wakati wa masika",
        "maharagwe aina bora Tanzania TARI",
        "ng'ombe hawali vizuri dalili za ugonjwa",
        "mihogo magonjwa na wadudu CMD",
        "mbolea ya NPK kwa mahindi kiasi gani kwa hekta",
        "fall army worm jinsi ya kuua mahindi",
        "umwagiliaji wa mpunga wakati wa kutoa maua",
    ]

    print("\n🧪 Kujaribu RAG Search System v4...")
    print("=" * 60)

    collection = get_collection()
    print(f"Chunks kwenye database: {collection.count()}\n")

    for q in queries:
        print(f"❓ {q}")
        results = search(q, n_results=2)
        if results:
            for r in results:
                print(f"   [{r['score']:.2f}] {r['title'][:52]}")
                print(f"        {r['text'][:130]}...")
        else:
            print("   ⚠️  Hakuna — jenga database: python rag/rag_system.py --build")
        print()

# ── Main ──────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Kilimo Bot RAG System v4"
    )
    parser.add_argument(
        "--build", action="store_true",
        help="Jenga/sasisha RAG database"
    )
    parser.add_argument(
        "--test", action="store_true",
        help="Jaribu mfumo wa kutafuta"
    )
    args = parser.parse_args()

    if args.build:
        build_database()
    elif args.test:
        test_search()
    else:
        print("\nKilimo Bot RAG System v4")
        print("Tumia:")
        print("  python rag/rag_system.py --build   ← jenga database")
        print("  python rag/rag_system.py --test    ← jaribu kutafuta")
        print(f"\nCollection: {COLLECTION_NAME}")
        try:
            c = get_collection()
            print(f"Chunks sasa hivi: {c.count()}")
        except:
            print("Database: haijajengwa bado")