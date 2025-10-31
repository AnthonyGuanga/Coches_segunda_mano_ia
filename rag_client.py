import os
from dotenv import load_dotenv
import google.generativeai as genai
import chromadb
from sentence_transformers import SentenceTransformer

load_dotenv()
# ===========================
# 🔑 Configurar Gemini
# ===========================
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
MODEL_NAME = "gemini-flash-latest"
model = genai.GenerativeModel(MODEL_NAME)

import os
from dotenv import load_dotenv
import google.generativeai as genai



# ===========================
# 📦 Conexión a la base vectorial (Chroma)
# ===========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db_coches")

client = chromadb.PersistentClient(path=DB_PATH)
collection = client.get_or_create_collection(name="coches_autofesa")

# ===========================
# 🧠 Modelo de embeddings 
# ===========================
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')


def query(user_question: str):
    """Realiza una consulta RAG usando Chroma y Gemini."""
    try:
        # 1️⃣ Validación de entrada
        if not user_question.strip():
            return {"success": False, "error": "La pregunta no puede estar vacía."}

        # 2️⃣ Vectorizar la pregunta del usuario
        query_embedding = embedding_model.encode([user_question]).tolist()

        # 3️⃣ Buscar documentos relevantes en Chroma
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=5
        )

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        if not docs or len(docs) == 0:
            return {"success": False, "error": "No se encontró contexto relevante."}

        # 4️⃣ Construir el contexto para Gemini
        contexto = ""
        for meta in metas:
            contexto += f"- {meta['modelo']} | {meta['precio']} | {meta['info']} | {meta['link']}\n"

        # 5️⃣ Crear prompt para Gemini
        prompt = f"""
Eres un asesor experto en coches de segunda mano.
Usa únicamente la información del contexto para responder la pregunta del cliente.
Si no tienes información suficiente, respóndele de forma amable y sugiere que afine su búsqueda.

📄 Contexto:
{contexto}

❓ Pregunta:
{user_question}

🧠 Respuesta:
"""

        # 6️⃣ Llamada a Gemini
        response = model.generate_content(prompt)
        return {"success": True, "answer": response.text}

    except Exception as e:
        return {"success": False, "error": str(e)}


# ✅ Para probar desde terminal:
# python3 -c "import rag_client; print(rag_client.query('Quiero un coche de gasolina por menos de 17000 euros'))"