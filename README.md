# 🌾 Kilimo Bot — AI Msaidizi wa Kilimo (Tanzania)

Kilimo Bot ni mfumo wa AI wa kilimo uliotengenezwa kwa Flask na Groq LLM, unaolenga kusaidia wakulima kupata majibu ya haraka, rahisi na ya vitendo kuhusu kilimo kwa kutumia Kiswahili au English.

Mfumo huu unatumia RAG (Retrieval-Augmented Generation) ili kuchukua taarifa kutoka kwenye nyaraka halisi za kilimo kama FAO, TARI, CIMMYT na IITA kisha kuzitumia kwenye kujibu maswali ya mtumiaji.

---

## 🌱 Kilimo Bot ni nini?

Kilimo Bot ni AI assistant wa kilimo anayefanya kazi kama mtaalamu wa kilimo wa kidigitali.

Anasaidia mkulima kuuliza maswali kama:
- Magonjwa ya mimea
- Mbegu bora
- Mbolea
- Udhibiti wa wadudu
- Hali ya hewa na athari zake
- Ushauri wa kilimo wa kila siku

Mfumo huu umejengwa kuwa:
- Rahisi kutumia
- Haraka kujibu
- Na unaoeleweka kwa wakulima wa kawaida

---

## 🎯 Inatatua tatizo gani?

Kilimo Bot ilijengwa kutatua changamoto halisi zinazowakumba wakulima:

### 1. 📉 Ukosefu wa taarifa sahihi za kilimo
Wakulima wengi hupata taarifa zisizo sahihi kutoka vyanzo visivyo rasmi.

👉 Kilimo Bot inatoa majibu yanayotegemea nyaraka za kitaalamu (FAO, TARI, CIMMYT).

---

### 2. ⏳ Kukosekana kwa wataalamu wa kilimo muda wote
Si kila mkulima anaweza kufikia mtaalamu wa kilimo kila wakati.

👉 Kilimo Bot inafanya kazi kama mtaalamu anayepatikana 24/7 kupitia chat.

---

### 3. 🌦️ Kutokuelewa hali ya hewa kwenye kilimo
Wakulima wengi hupata ugumu kuelewa athari za hali ya hewa kwenye mazao.

👉 Mfumo unaeleza hali ya hewa kwa mtazamo wa kilimo (agricultural interpretation) pale inapoulizwa.

---

### 4. 📚 Taarifa za kilimo kutawanyika
Taarifa zipo kwenye PDF nyingi na reports tofauti.

👉 Kilimo Bot huzikusanya, huzichakata na kuzitumia kujibu maswali kwa haraka.

---
## 🏗️ Architecture ya Mfumo

Kilimo Bot inafanya kazi kwa architecture rahisi ya AI + RAG:

│
▼
Flask API (app.py)
│
├── RAG System (PDF chunks + keyword search)
├── Farmer Profile (mkoa + zao memory)
├── Weather Context (ikiwa imeombwa)
│
▼
Context Builder (system prompt)
│
▼
Groq LLM (AI engine)
│
▼
Response kwa User

---

## ⚙️ Muhtasari wa Flow

User anauliza swali → mfumo unatafuta taarifa (RAG + profile + weather) → unachanganya context → unapeleka kwa Groq LLM → AI inatoa jibu la mwisho.

---

## 💡 Idea Kuu

Kilimo Bot si model kubwa ya AI, bali ni **orchestration system** inayochanganya:
- Knowledge retrieval (RAG)
- User context (profile)
- AI generation (Groq LLM)


## ⚙️ Jinsi inavyofanya kazi

Mfumo wa Kilimo Bot unafanya kazi kwa hatua rahisi:

1. 📄 PDFs za kilimo hupakuliwa na kuhifadhiwa
2. ✂️ Maandishi hugawanywa (chunking) kuwa vipande vidogo
3. 🔎 Mfumo hutafuta vipande vinavyofanana na swali la mtumiaji (keyword-based RAG)
4. 🧠 Vipande vinatumwa kwa Groq LLM
5. 💬 AI inatoa jibu la mwisho lenye muktadha wa kilimo

---

## 🧩 Muundo wa Mfumo

Kilimo Bot ni mfumo rahisi lakini wenye nguvu ya practical AI:

- **Flask** — backend ya API na chat system
- **Groq LLM** — injini ya AI ya majibu ya haraka
- **RAG Engine (lightweight)** — keyword + overlap retrieval
- ** PostgreSQL** — kuhifadhi history ya mazungumzo
- **PyMuPDF** — kusoma PDFs za kilimo
- **Docker** — deployment rahisi
- **Render** — hosting ya cloud

---

## 🧠 RAG (Knowledge System)

Mfumo wa RAG unafanya kazi bila kutumia ML models nzito.

Badala ya hiyo:
- Unatumia keyword matching
- Text overlap scoring
- Document chunking

👉 Hii inafanya system iwe:
- Lightweight
- Haraka
- Inafaa free hosting (Render)

---

## ⚖️ Ukweli kuhusu mfumo huu

Kilimo Bot si mfumo perfect.

- Wakati mwingine inaweza kukosa majibu kama data haipo kwenye PDFs
- Inategemea ubora wa documents zilizopo
- Si mbadala wa mtaalamu wa shamba (field expert)

Lakini:

👉 Ni **rahisi kutumia**
👉 Ni **haraka**
👉 Ni **practical kwa wakulima wa kawaida**
👉 Imejengwa kwa mazingira ya real-world constraints (low resources)

---

## 🚀 Lengo la Mradi

Lengo la Kilimo Bot ni:

👉 Kufanya maarifa ya kilimo yawe rahisi kupatikana
👉 Kusaidia wakulima kufanya maamuzi bora
👉 Kuleta AI kwenye kilimo cha Afrika kwa lugha rahisi ya mkulima

---

## 🛠️ Tech Stack

- Python (Flask)
- Groq API (LLM)
- PyMuPDF
-  PostgreSQL
- Docker
- Render

---

## 📌 Hitimisho

Kilimo Bot ni mfumo wa AI wa kilimo uliojengwa kwa simplicity na practicality.

Si perfect, lakini ni hatua ya kuelekea:
👉 Smart farming systems zinazoweza kutumika na wakulima wa kawaida Afrika Mashariki.


UNAWEZA KUONA JINSI INAVYOFANYA KAZI KUPITIA 
https://killimo-boat.onrender.com




---
