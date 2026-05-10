from flask import Flask, render_template, request, jsonify
from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

chat_history = []

SYSTEM_PROMPT = """Wewe ni mtaalamu wa kilimo anayeitwa Kilimo Bot..."""

# ======================
# LAZY RAG SETUP
# ======================
_retriever = None

def get_retriever():
    global _retriever
    if _retriever is None:
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
        _retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    return _retriever

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

    chat_history.append({"role": "user", "content": user_message})

    try:
        docs = get_retriever().invoke(user_message)
        context = "\n".join([d.page_content for d in docs])

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "system", "content": context},
                *chat_history[-20:]
            ],
            max_tokens=1024
        )

        ai_reply = response.choices[0].message.content
        chat_history.append({"role": "assistant", "content": ai_reply})
        return jsonify({"reply": ai_reply})

    except Exception as e:
        chat_history.pop()
        return jsonify({"error": str(e)}), 500


@app.route("/clear", methods=["POST"])
def clear():
    chat_history.clear()
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)