"""
rag/rag_system.py
-----------------
RAG mpya inayotumia Groq API moja kwa moja.
Hakuna sentence-transformers, hakuna ChromaDB.
RAM inayohitajika: ~50MB tu (inafanya kazi Render free tier)

Jinsi inavyofanya kazi:
1. PDF content imehifadhiwa kama maandishi kwenye data/chunks/
2. Swali linapokuja — tafuta chunks zinazofanana kwa keyword matching
3. Tuma chunks zilizochaguliwa kwa Groq — yeye anatoa jibu
"""

import os
import json
import re
import fitz  # PyMuPDF
import requests

# ── Paths ──────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR     = os.path.join(BASE_DIR, "data", "pdfs")
CHUNKS_DIR  = os.path.join(BASE_DIR, "data", "chunks")
os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(CHUNKS_DIR, exist_ok=True)

# ── Documents ──────────────────────────────────────────────────
DOCUMENTS = [
    {
        "id": "maize_manual_tz",
        "title": "Maize Production Manual Tanzania",
        "source": "IITA / TARI / USAID",
        "url": "https://cgspace.cgiar.org/server/api/core/bitstreams/a5a24307-e6c2-40cd-9138-493f8ff0e94a/content",
        "keywords": ["mahindi", "maize", "corn", "mbolea", "fertilizer", "wadudu", "pest", "fall army worm", "FAW", "stem borer", "kupanda", "harvesting", "mavuno"],
    },
    {
        "id": "maize_value_chain_tz",
        "title": "Maize Value Chain Tanzania",
        "source": "FAO Tanzania",
        "url": "https://www.fao.org/fileadmin/user_upload/ivc/PDF/SFVC/Tanzania_maize.pdf",
        "keywords": ["mahindi", "maize", "soko", "market", "bei", "price", "wakulima"],
    },
    {
        "id": "maize_diseases_africa",
        "title": "Maize Diseases and Pests in Africa",
        "source": "CIMMYT",
        "url": "https://repository.cimmyt.org/bitstream/handle/10883/1262/9031.pdf",
        "keywords": ["mahindi", "maize", "magonjwa", "disease", "wadudu", "pest", "madoa", "streak", "blight", "rust", "armyworm"],
    },
    {
        "id": "rice_value_chain_tz",
        "title": "Rice Value Chain Tanzania",
        "source": "FAO Tanzania",
        "url": "https://www.fao.org/fileadmin/user_upload/ivc/PDF/SFVC/Tanzania_rice.pdf",
        "keywords": ["mpunga", "rice", "paddy", "umwagiliaji", "irrigation", "blast", "borer", "kupanda"],
    },
    {
        "id": "beans_variety_catalogue_tari",
        "title": "Bean Variety Catalogue Tanzania",
        "source": "TARI",
        "url": "https://www.tari.go.tz/assets/uploads/documents/ea8db0325b3534ca3fec5354ea51d255.pdf",
        "keywords": ["maharagwe", "beans", "aina", "variety", "mbegu", "seed", "TARI"],
    },
    {
        "id": "tomato_ipm_fao",
        "title": "Tomato Integrated Pest Management",
        "source": "FAO / CABI",
        "url": "https://openknowledge.fao.org/server/api/core/bitstreams/79f188d5-64cf-49a0-b924-47bc7a184eb5/content",
        "keywords": ["nyanya", "tomato", "wadudu", "pest", "magonjwa", "disease", "tuta", "blight", "IPM"],
    },
    {
        "id": "cassava_africa_fao",
        "title": "Cassava in Africa - Tanzania",
        "source": "FAO",
        "url": "https://www.fao.org/4/a0154e/a0154e09.htm",
        "keywords": ["mihogo", "cassava", "CMD", "CBSD", "magonjwa", "disease", "whitefly", "mealybug"],
    },
    {
        "id": "tz_climate_smart_agriculture",
        "title": "Tanzania Climate Smart Agriculture",
        "source": "FAO / Serikali ya Tanzania",
        "url": "https://faolex.fao.org/docs/pdf/tan215306.pdf",
        "keywords": ["hali ya hewa", "climate", "mvua", "rainfall", "ukame", "drought", "misimu", "season"],
    },
    {
        "id": "fao_tz_country_crops",
        "title": "Tanzania Country Report FAO",
        "source": "FAO",
        "url": "https://www.fao.org/fileadmin/templates/agphome/documents/PGR/SoW1/africa/TANZANIA.pdf",
        "keywords": ["mazao", "crops", "mbegu", "seeds", "Tanzania", "aina", "varieties"],
    },
    {
        "id": "livestock_tz_bioenergy",
        "title": "Tanzania Livestock and Food Security",
        "source": "FAO",
        "url": "https://www.fao.org/4/aq179e/aq179e.pdf",
        "keywords": ["mifugo", "livestock", "ng'ombe", "cattle", "kuku", "chicken", "magonjwa", "disease"],
    },
]

# ── Pakua PDF na hifadhi chunks ────────────────────────────────
def download_pdf(url, save_path):
    if os.path.exists(save_path):
        return True
    try:
        r = requests.get(url, timeout=30, stream=True,
                        headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"  [fail] {e}")
        return False

def fetch_html(url):
    try:
        r = requests.get(url, timeout=15,
                        headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        text = re.sub(r'<[^>]+>', ' ', r.text)
        return re.sub(r'\s+', ' ', text).strip()
    except:
        return ""

def extract_pdf_text(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        text = "".join(page.get_text() for page in doc)
        doc.close()
        return text
    except:
        return ""

def chunk_text(text, chunk_size=400, overlap=50):
    """Gawanya maandishi kwa vipande — chuja jedwali."""
    text = re.sub(r'\s+', ' ', text).strip()
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks, current, current_len = [], [], 0

    for sent in sentences:
        words = sent.split()
        if len(words) < 6:
            continue
        # Chuja jedwali — alpha ratio
        alpha = sum(c.isalpha() for c in sent) / max(len(sent), 1)
        if alpha < 0.4:
            continue

        if current_len + len(words) > chunk_size and current:
            chunk_str = ' '.join(current)
            if len(chunk_str.split()) >= 30:
                chunks.append(chunk_str)
            current = current[-2:]
            current_len = sum(len(s.split()) for s in current)

        current.append(sent)
        current_len += len(words)

    if current:
        chunk_str = ' '.join(current)
        if len(chunk_str.split()) >= 30:
            chunks.append(chunk_str)

    return chunks

def build_chunks():
    """Pakua PDFs na hifadhi chunks kama JSON files."""
    print("\n🌾 Kujenga RAG Chunks (Groq-based)...")
    print("=" * 55)

    total = 0
    for doc in DOCUMENTS:
        chunks_file = os.path.join(CHUNKS_DIR, f"{doc['id']}.json")

        if os.path.exists(chunks_file):
            with open(chunks_file) as f:
                existing = json.load(f)
            print(f"  [cache] {doc['id']} — chunks {len(existing)}")
            total += len(existing)
            continue

        print(f"\n📄 {doc['title'][:50]}...")
        is_html = "htm" in doc["url"] and not doc["url"].endswith(".pdf")

        if is_html:
            text = fetch_html(doc["url"])
        else:
            pdf_path = os.path.join(PDF_DIR, f"{doc['id']}.pdf")
            ok = download_pdf(doc["url"], pdf_path)
            text = extract_pdf_text(pdf_path) if ok else ""

        if not text or len(text.split()) < 100:
            print(f"  ⚠️  Imeachwa")
            continue

        chunks = chunk_text(text)
        print(f"  Maneno: {len(text.split()):,} → Chunks: {len(chunks)}")

        # Hifadhi chunks na metadata
        data = {
            "id": doc["id"],
            "title": doc["title"],
            "source": doc["source"],
            "keywords": doc["keywords"],
            "chunks": chunks
        }
        with open(chunks_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        total += len(chunks)
        print(f"  ✅ Imehifadhiwa")

    print(f"\n✅ Jumla ya chunks: {total}")
    return total

# ── Tafuta chunks zinazofanana na swali ────────────────────────
def search(query, n_results=4):
    """
    Tafuta kwa keyword matching — rahisi, haraka, hakuna RAM nyingi.
    Inarudisha chunks zinazofanana na swali.
    """
    query_lower = query.lower()
    query_words = set(re.findall(r'\b\w+\b', query_lower))

    scored = []

    for doc in DOCUMENTS:
        chunks_file = os.path.join(CHUNKS_DIR, f"{doc['id']}.json")
        if not os.path.exists(chunks_file):
            continue

        try:
            with open(chunks_file, encoding="utf-8") as f:
                data = json.load(f)
        except:
            continue

        # Score kwa keywords za document
        doc_keywords = [k.lower() for k in data.get("keywords", [])]
        keyword_score = sum(1 for kw in doc_keywords if kw in query_lower)

        if keyword_score == 0:
            continue

        # Tafuta chunks zinazofanana zaidi
        for chunk in data.get("chunks", []):
            chunk_lower = chunk.lower()
            chunk_words = set(re.findall(r'\b\w+\b', chunk_lower))

            # Hesabu overlap ya maneno
            overlap = len(query_words & chunk_words)
            total_score = keyword_score * 2 + overlap

            if total_score > 0:
                scored.append({
                    "text": chunk,
                    "title": data["title"],
                    "source": data["source"],
                    "score": total_score,
                })

    # Panga kwa score — chukua bora
    scored.sort(key=lambda x: x["score"], reverse=True)

    # Ondoa duplicates — chukua tofauti
    seen = set()
    unique = []
    for item in scored:
        key = item["text"][:100]
        if key not in seen:
            seen.add(key)
            unique.append(item)
        if len(unique) >= n_results:
            break

    return unique

def format_context(results):
    """Tengeneza context string kutoka search results."""
    if not results:
        return ""
    parts = []
    for r in results:
        parts.append(
            f"--- Chanzo: {r['title']} ({r['source']}) ---\n{r['text']}"
        )
    return "\n\n".join(parts)

# ── Build ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if "--build" in sys.argv:
        build_chunks()
    elif "--test" in sys.argv:
        queries = [
            "mahindi yana madoa meupe ni ugonjwa gani",
            "fall army worm jinsi ya kuua",
            "nyanya magonjwa ya ukungu",
            "mpunga blast ugonjwa",
            "maharagwe aina bora Tanzania",
        ]
        print("\n🧪 Kujaribu RAG Search (Groq-based)...")
        print("=" * 55)
        for q in queries:
            print(f"\n❓ {q}")
            results = search(q, n_results=2)
            if results:
                for r in results:
                    print(f"   [score:{r['score']}] {r['title'][:45]}")
                    print(f"   {r['text'][:120]}...")
            else:
                print("   ⚠️  Hakuna — jenga kwanza: python rag/rag_system.py --build")
    else:
        print("Tumia:")
        print("  python rag/rag_system.py --build")
        print("  python rag/rag_system.py --test")
