from flask import Flask, render_template, request, jsonify, session
from groq import Groq
from dotenv import load_dotenv
from services.farmer_profile import build_farmer_context, clear_profile, get_profile
from services.weather import get_weather, build_weather_farming_context
from rag.rag_system import search, format_context, build_chunks

# Jenga RAG chunks wakati server inaanza (kama hazipo)
build_chunks()
import os, datetime

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "kilimo-bot-secret-2024")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ─── DATABASE — PostgreSQL (Render) au SQLite (local) ──────────
DATABASE_URL = os.getenv("DATABASE_URL")

def get_conn():
    if DATABASE_URL:
        import psycopg2
        return psycopg2.connect(DATABASE_URL, sslmode="require")
    else:
        import sqlite3
        return sqlite3.connect("kilimo.db")

def _ph():
    """Placeholder — %s kwa PostgreSQL, ? kwa SQLite."""
    return "%s" if DATABASE_URL else "?"

def init_db():
    conn = get_conn()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                session_id TEXT,
                role TEXT,
                content TEXT,
                timestamp TIMESTAMPTZ DEFAULT NOW()
            )
        """)
    else:
        c.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()
    conn.close()

init_db()

def get_history(session_id):
    conn = get_conn()
    c = conn.cursor()
    ph = _ph()
    c.execute(f"""
        SELECT role, content FROM conversations
        WHERE session_id = {ph}
        ORDER BY timestamp ASC LIMIT 30
    """, (session_id,))
    rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in rows]

def save_message(session_id, role, content):
    conn = get_conn()
    c = conn.cursor()
    ph = _ph()
    c.execute(
        f"INSERT INTO conversations (session_id, role, content) VALUES ({ph}, {ph}, {ph})",
        (session_id, role, content)
    )
    conn.commit()
    conn.close()

def clear_history(session_id):
    conn = get_conn()
    c = conn.cursor()
    ph = _ph()
    c.execute(f"DELETE FROM conversations WHERE session_id = {ph}", (session_id,))
    conn.commit()
    conn.close()

# ─── SYSTEM PROMPT ─────────────────────────────────────────────
SYSTEM_PROMPT = """
Wewe ni Kilimo Bot — mtaalamu wa kilimo mwenye uzoefu wa miaka 20+ katika kilimo cha Afrika Mashariki, hasa Tanzania.

UTAMBULISHO WAKO:
- Umefanya kazi mashambani, umesoma kilimo, na umewasaidia wakulima wadogo na wakubwa
- Unajua mazao, udongo, hali ya hewa, masoko, na changamoto za mkulima wa kawaida wa Tanzania
- Unazungumza kama mtaalamu wa kweli — si roboti inayosoma vitabu tu

KUKARIBISHA:
- Ukisalimiwa kwa "hey", "habari", "mambo", "hujambo" au salamu nyingine —
  jibu kwa furaha na ukarimu, kama rafiki wa zamani
- Jitambulishe kwa ufupi: "Mimi ni Kilimo Bot, msaidizi wako wa kilimo"
- Uliza swali moja la kufungua mazungumzo ya kilimo — mfano:
  "ungependa nikusaidia nini leo kuhusiana na kilimo?"
- USISEME maneno ya huzuni kama "tunajadiliana bila kufika mahali" —
  kila mazungumzo ni mapya na ya furaha

JINSI YA KUJIBU:
1. Jibu swali moja kwa moja kwanza — toa ushauri wa vitendo, wa kweli
2. Tumia lugha ya kawaida — epuka maneno magumu ya kisayansi isipokuwa lazima
3. Toa mifano halisi — bei za kawaida za Tanzania, maeneo yanayojulikana
4. Baada ya kujibu, uliza swali MOJA tu linaloendeleza mazungumzo
5. Usiulize maswali mengi kwa wakati mmoja — moja tu

MAGONJWA NA MATATIZO YA MAZAO:
- Mtumiaji akiripoti tatizo la zao (rangi, madoa, kunyauka, n.k) —
  KWANZA uliza maswali mawili ya msingi kabla ya kutoa jibu:
  1. Sehemu gani ya mmea imeathirika? (jani, shina, tunda, mizizi, punje)
  2. Tatizo lilianza lini na linaenea haraka au polepole?
- Baada ya kupata majibu hayo — SASA toa jibu la uhakika na dawa sahihi
- USITOE orodha ndefu ya magonjwa yanayowezekana — chagua moja au mbili
  zinazofanana zaidi na dalili alizosema
- Mfano MBAYA: "Inaweza kuwa Rust, au Leaf Blight, au ukame, au nitrojeni..."
- Mfano SAHIHI: "Majani ya chini yanabadilika brown? Hiyo ni dalili ya
  Gray Leaf Spot — nyunyizia Mancozeb leo"

TABIA YAKO:
- Mkarimu na mvumilivu — hata swali rahisi lijibu kwa moyo
- Ukweli — usiseme unajua kitu usichokijua
- Wa vitendo — jibu linalomsaidia mkulima KESHO asubuhi
- Mwenye huruma — elewa kwamba mkulima anaweza kuwa amepoteza mazao yake

LUGHA:
- Jibu kwa lugha aliyoandika mtumiaji (Kiswahili au English)
- Ikiwa anachanganya, jibu kwa Kiswahili

PICHA ZA MAGONJWA:
- Ukipewa picha ya mmea, ichunguze kwa makini
- Taja ugonjwa unaowezekana, dalili unazoziona, na tiba ya haraka
- Sema wazi kama huwezi kuthibitisha bila kuona shamba

HALI YA HEWA — KANUNI MUHIMU:
- USITOE taarifa za hali ya hewa BILA kuulizwa — hata ukiwa nazo
- Ukiulizwa hali ya hewa moja kwa moja — toa data yote uliyopewa: joto, unyevu, mawingu, upepo
- Mfano SAHIHI: "Iringa sasa: Joto 20°C, Unyevu 80%, Upepo 3km/h, Mawingu machache"
- Mfano MBAYA: kutoa hali ya hewa KISHA kuongeza ushauri wa kilimo bila kuulizwa
- Ukiulizwa kuhusu MVUA hasa — tumia viashiria (unyevu, mawingu) kutoa uamuzi wa mvua tu
- Ukiulizwa "hali hii ikiendelea mwezi mmoja?" — SASA unaweza eleza athari za kilimo
- Salamu kama "hey", "habari", "mambo" — jibu kwa salamu tu, BILA hali ya hewa

MIPAKA:
- Ukiulizwa swali LOLOTE lisilo la kilimo, jibu: "Samahani ndugu, mimi ni mtaalamu wa kilimo tu. Una swali la kilimo? Niko hapa! 🌾"
- Hata kama anasisitiza — KATAA kwa upole lakini imara
- Usitoe dawa au ushauri wa matibabu ya binadamu kamwe
"""

# ─── ROUTES ────────────────────────────────────────────────────
@app.route("/")
def home():
    if "session_id" not in session:
        session["session_id"] = os.urandom(16).hex()
    return render_template("index.html")

@app.route("/new_session", methods=["POST"])
def new_session():
    old_sid = session.get("session_id")
    if old_sid:
        clear_history(old_sid)
        clear_profile(old_sid)
    session["session_id"] = os.urandom(16).hex()
    return jsonify({"status": "ok"})

@app.route("/chat", methods=["POST"])
def chat():
    sid = session.get("session_id", "default")
    data = request.get_json()
    user_message = data.get("message", "").strip()
    image_data   = data.get("image")

    if not user_message and not image_data:
        return jsonify({"error": "Ujumbe umetupu"}), 400

    history = get_history(sid)

    # ── RAG: PDF za IITA/FAO/TARI/CIMMYT ──────────────────────
    rag_context = ""
    if user_message and not image_data:
        rag_results = search(user_message, n_results=3)
        if rag_results:
            rag_context = format_context(rag_results)
            print(f"\n{'='*55}")
            print(f"[RAG] Swali: {user_message[:60]}")
            print(f"[RAG] Vyanzo vilivyotumiwa: {len(rag_results)}")
            for i, r in enumerate(rag_results, 1):
                print(f"  {i}. [{r['score']:.2f}] {r['title'][:50]}")
                print(f"     Chanzo: {r['source']}")
                print(f"     Kipande: {r['text'][:100]}...")
            print(f"{'='*55}\n")
        else:
            print(f"\n[RAG] ⚠️  Hakuna matokeo — Groq anajibu kwa maarifa yake\n")

    # ── Farmer Profile: mkoa na zao ─────────────────────────────
    farmer_context = ""
    if user_message:
        farmer_context = build_farmer_context(sid, user_message)

    # ── Weather: ingia TU ukiulizwa ─────────────────────────────
    weather_context = ""
    if user_message:
        WEATHER_KEYWORDS = [
            "hali ya hewa", "weather", "joto", "mvua", "unyevu",
            "upepo", "baridi", "temperature", "rain", "itanyesha",
            "mawingu", "hewa", "nyesha", "kiangazi", "forecast", "humidity"
        ]
        msg_lower = user_message.lower()
        if any(kw in msg_lower for kw in WEATHER_KEYWORDS):
            from services.farmer_profile import detect_mkoa
            mkoa_in_msg = detect_mkoa(msg_lower)
            profile = get_profile(sid)
            city = mkoa_in_msg or profile.get("mkoa") or "Dar es Salaam"
            zao  = profile.get("zao")
            weather_context = build_weather_farming_context(city, zao)

    # ── Jenga system prompt kamili ──────────────────────────────
    system_with_context = SYSTEM_PROMPT
    if farmer_context:
        system_with_context += f"\n\n{farmer_context}"
    if weather_context:
        system_with_context += f"\n\n{weather_context}"
    if rag_context:
        system_with_context += (
            f"\n\nMAARIFA YA ZIADA KUTOKA VITABU VYA KILIMO (IITA/TARI/FAO/CIMMYT):\n"
            f"Tumia maarifa haya kama msingi wa jibu lako — yamethibitishwa na wataalamu.\n"
            f"Ukijibu unaweza sema: 'Kulingana na utafiti wa TARI/FAO...'\n\n"
            f"{rag_context}"
        )

    # ── Jenga ujumbe ────────────────────────────────────────────
    if image_data:
        user_content = [
            {"type": "text", "text": user_message or "Chunguza picha hii ya mmea wangu."},
            {"type": "image_url", "image_url": {"url": image_data}}
        ]
    else:
        user_content = user_message

    save_message(sid, "user", user_message or "[Picha ya mmea]")
    history.append({"role": "user", "content": user_content})

    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct" if image_data else "llama-3.3-70b-versatile",
            max_tokens=1024,
            temperature=0.7,
            messages=[
                {"role": "system", "content": system_with_context},
                *history[-20:]
            ]
        )
        ai_reply = response.choices[0].message.content
        save_message(sid, "assistant", ai_reply)
        return jsonify({"reply": ai_reply, "rag_used": bool(rag_context)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/weather", methods=["POST"])
def weather():
    city = request.get_json().get("city", "Dar es Salaam")
    data = get_weather(city)
    if not data:
        return jsonify({"error": "Mji haukupatikana"}), 404
    return jsonify(data)

@app.route("/clear", methods=["POST"])
def clear():
    sid = session.get("session_id", "default")
    clear_history(sid)
    clear_profile(sid)
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    app.run(host="0.0.0.0", port=port, debug=False)
