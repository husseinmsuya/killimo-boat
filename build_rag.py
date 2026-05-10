from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

files = [
    "data/crops.txt",
    "data/fertilizer.txt",
    "data/diseases.txt",
    "data/pests.txt",
    "data/irrigation.txt",
    "data/regions.txt",
    "data/faq.txt"
]

docs = []

# Load files
for file in files:
    loader = TextLoader(file, encoding="utf-8")
    docs.extend(loader.load())

# Split text
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)

chunks = splitter.split_documents(docs)

# Embeddings
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# Create vector DB
vectorstore = FAISS.from_documents(
    chunks,
    embeddings
)

# Save index
vectorstore.save_local("faiss_index")

print("RAG indexed successfully")