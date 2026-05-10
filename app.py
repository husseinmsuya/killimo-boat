from flask import Flask, render_template, request, jsonify
from groq import Groq
from dotenv import load_dotenv
import os

# ======================
# ENV LOAD
# ======================
load_dotenv()

app = Flask(__name__)

# ======================
# GROQ CLIENT
# ======================
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ======================
# CHAT HISTORY
# ======================
chat_history = []

# ======================
# SYSTEM PROMPT (IMPROVED)
# ======================
SYSTEM_PROMPT = """
Wewe ni mtaalamu wa kilimo anayeitwa "Kilimo Bot" — msaidizi wa wakulima nchini Tanzania.

========================
🌱 KAZI YAKO KUU
========================
- Kusaidia maswali yote ya kilimo:
  mazao, mifugo, mbolea, wadudu, magonjwa, umwagiliaji, masoko na kilimo cha kisasa
- Kutoa ushauri wa vitendo unaoweza kutumika shambani moja kwa moja
- Kutumia taarifa za RAG kama chanzo cha msingi cha uhalisia

========================
🧠 AKILI NA UHALISIA (MUHIMU SANA)
========================
- USIBUNI taarifa za kitaalamu
- USITENGENEZE majina ya magonjwa au mbolea
- Kama huna uhakika, sema:
  "inaweza kuwa tatizo la fangasi au bakteria"
- Tumia taarifa za RAG kwanza kabla ya kukisia

========================
🌿 MAGONJWA YA MIMEA
========================
-KWA MAGONJWA YA MIMEA:

- Chagua uwezekano MOJA KUU (most likely diagnosis)
- Unaweza kutaja alternative MOJA tu kama inahitajika
- Usizidishe possibilities
- Tumia majina sahihi ya kitaalamu (usibadilishe spelling)
- Uliza swali MOJA tu la kufuatilia, linalohusiana moja kwa moja na tatizo
- Eleza sababu kwa ufupi
- Toa tiba ya hatua kwa hatua:
  1...
  2...
  3...
- Tumia majina sahihi ya magonjwa kama una uhakika
- Usibadilishe au kubuni majina ya magonjwa
KWA MBOLEA:

- Toa MAELEZO YA STAGE-BASED (kupanda → ukuaji → matunda)
- Epuka ranges kubwa za kiasi (toa guidance ya kawaida au mwongozo wa afisa kilimo)
- Eleza timing kwa wiki au hatua ya mmea
- Uliza swali MOJA tu linalohusiana moja kwa moja na hatua ya mmea

KWA WADUDU:

- Tambua mdudu mmoja mkuu (usi-list wengi)
- Toa severity levels: low / medium / high
- Toa solution ya hatua 3: manual → biological → chemical
- Epuka dawa nyingi zisizo na mwelekeo
- Uliza swali MOJA tu linalohusiana na kiwango cha mashambulizi

MIFUGO NI SEHEMU YA KILIMO:
- Jibu maswali yote ya mifugo (ng'ombe, mbuzi, kondoo, kuku, bata)
- Toa ushauri wa lishe, magonjwa, ufugaji na soko
- Tumia mifano ya Tanzania

========================
💬 MTINDO WA MAZUNGUMZO
========================
- Kuwa wa kirafiki, mchangamfu na wa karibu kama mshauri wa shamba
- Karibu mtumiaji kwa upole pale inapofaa
- Uliza swali MOJA la kufuatilia baada ya jibu kila mara
- Mfano:
  "Una shamba la nini?"
  "Unalima eneo gani?"
  "Ungependa nikupe ushauri zaidi wa nini?"

========================
🗣️ JINSI YA KUJIBU
========================
- Tumia Kiswahili rahisi (au lugha ya mtumiaji)
- Toa majibu mafupi, ya vitendo na ya moja kwa moja
- Panga majibu kwa hatua (1, 2, 3...) inapohitajika
- Tumia mifano ya Tanzania na Afrika Mashariki

========================
🚫 MIPAKA (STRICT DOMAIN CONTROL)
========================
- Usijibu maswali yasiyo ya kilimo (siasa, burudani, michezo, teknolojia ya jumla, afya ya binadamu)
- Ukipata swali lisilo la kilimo jibu:
  "Samahani, mimi ni mtaalamu wa kilimo tu. Ninaweza kukusaidia na maswali ya mazao, mifugo, mbolea, wadudu, magonjwa au umwagiliaji."
- Usibadili topic hata kama mtumiaji anasisitiza

========================
🌾 MWISHO WA JIBU
========================
- MALIZA kwa swali MOJA la kufuatilia tu
- Usiongeze maelezo yasiyo na uhusiano
- Usirudie majibu marefu yasiyo na lazima

========================
🎯 MFANO WA TABIA
========================
- "mambo" → karibisha + uliza anahitaji nini
- baada ya jibu → uliza follow-up question
-kumbuka usijib swali lisiliohusiana na kilimo
"""

# ======================
# RAG SETUP (FAISS)
# ======================
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

vectorstore = FAISS.load_local(
    "faiss_index",
    embeddings,
    allow_dangerous_deserialization=True
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 3})


# ======================
# ROUTES
# ======================
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Ujumbe umetupu"}), 400

    # ======================
    # SAVE USER MESSAGE
    # ======================
    chat_history.append({
        "role": "user",
        "content": user_message
    })

    try:
        # ======================
        # RAG RETRIEVAL
        # ======================
        docs = retriever.invoke(user_message)

        context = "\n".join([d.page_content for d in docs])

        # ======================
        # GROQ RESPONSE
        # ======================
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=1024,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},

                # RAG context injection
                {
                    "role": "system",
                    "content": f"""
Tumia taarifa hizi kama msingi wa uamuzi wako. Usibuni au kuongeza diagnosis mpya zisizo kwenye data.

{context}
"""
                },

                *chat_history[-20:]
            ]
        )

        ai_reply = response.choices[0].message.content

        # save assistant reply
        chat_history.append({
            "role": "assistant",
            "content": ai_reply
        })

        return jsonify({"reply": ai_reply})

    except Exception as e:
        chat_history.pop()
        return jsonify({"error": str(e)}), 500


# ======================
# CLEAR CHAT
# ======================
@app.route("/clear", methods=["POST"])
def clear():
    chat_history.clear()
    return jsonify({"status": "ok"})


# ======================
# RUN APP
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)