import os
import re
import pandas as pd
from typing import Optional
from dotenv import load_dotenv

# === LangChain ===
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain_core.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI

# === UI ===
import gradio as gr

load_dotenv()

# =====================================================================================
#                               CONFIGURACIÓN GLOBAL
# =====================================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")
COLLECTION_NAME = "inventario_coches_autofesa"
CSV_PATH = os.path.join(BASE_DIR, "autofesa_completo_20251127_1041.csv")

GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_KEY:
    raise ValueError("❌ GOOGLE_API_KEY no está definido en .env")


# =====================================================================================
#                                   CARGA CSV
# =====================================================================================

def crear_documentos_desde_csv(csv_path: str):
    print(f"Loading CSV: {csv_path}")

    df = pd.read_csv(csv_path)
    docs = []

    for _, row in df.iterrows():
        text = (
            f"Modelo: {row['Modelo']}. Precio: {row['Precio']}€. Año: {row['Año']}. "
            f"Kilometraje: {row['Km']} km. Combustible: {row['Combustible']}. "
            f"Link: {row['Link']}"
        )

        docs.append(
            Document(
                page_content=text,
                metadata=dict(
                    Modelo=row["Modelo"],
                    Precio=row["Precio"],
                    Km=row["Km"],
                    Año=row["Año"],
                    Link=row["Link"],
                    Combustible=row["Combustible"],
                ),
            )
        )

    print(f"Created {len(docs)} documents.")
    return docs


# =====================================================================================
#                                 FILTRADO ESTRICTO
# =====================================================================================

def filtrar_coches_por_parametros(raw: str, max_precio=None, max_km=None):
    if not raw or "No se encontraron" in raw:
        return raw

    coches = [c.strip() for c in raw.split(";") if c.strip()]

    regex = re.compile(
        r"\[(\d+)\s*€\].*?\((?:.*?)\s*(\d+)\s*km",
        flags=re.IGNORECASE,
    )

    filtrados = []
    for c in coches:
        match = regex.search(c)
        if not match:
            continue

        precio = int(match.group(1))
        km = int(match.group(2))

        if (max_precio is None or precio <= max_precio) and (
            max_km is None or km <= max_km
        ):
            filtrados.append(c)

    if not filtrados:
        return "No se encontraron coches que cumplan esos criterios de filtrado estricto."

    return "; ".join(filtrados)


# =====================================================================================
#                                 CONFIGURAR RAG
# =====================================================================================

docs = crear_documentos_desde_csv(CSV_PATH)

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

vectorstore = Chroma.from_documents(
    documents=docs,
    embedding=embeddings,
    persist_directory=CHROMA_DIR,
    collection_name=COLLECTION_NAME,
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

prompt = PromptTemplate(
    template="""
Eres un buscador experto del inventario Autofesa.

Usa SOLO el contexto para responder.
Devuelve resultados usando este formato:

Modelo [Precio€] (Combustible, Km, Año); Modelo2 [Precio€] (...)

Si no encuentras coincidencias, responde:
"No se encontraron coches que cumplan esos criterios en el inventario."

Pregunta: {question}
Contexto: {context}
""",
    input_variables=["context", "question"],
)

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=GOOGLE_KEY,
    temperature=0,
)

rag_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever,
    return_source_documents=False,
    chain_type_kwargs={"prompt": prompt},
)


# =====================================================================================
#                         FUNCIÓN PRINCIPAL QUE USA RAG
# =====================================================================================

def buscar_coches_rag(query: str, max_precio=None, max_km=None):
    result = rag_chain.invoke({"query": query})
    raw = result["result"].strip()

    return filtrar_coches_por_parametros(raw, max_precio, max_km)


# =====================================================================================
#                                   GRADIO
# =====================================================================================

def consultar(pregunta, max_precio, max_km):
    max_precio = int(max_precio) if max_precio else None
    max_km = int(max_km) if max_km else None

    return buscar_coches_rag(pregunta, max_precio, max_km)


with gr.Blocks(title="RAG Autofesa") as demo:
    gr.Markdown("# 🚗 Buscador Inteligente Autofesa (RAG + Gemini)")

    pregunta = gr.Textbox(label="Consulta", placeholder="coches BMW diesel…")
    max_precio = gr.Number(label="Precio máximo", value=None)
    max_km = gr.Number(label="Kilometraje máximo", value=None)

    out = gr.Textbox(label="Resultado", lines=6)

    gr.Button("Buscar").click(
        consultar,
        inputs=[pregunta, max_precio, max_km],
        outputs=out,
    )


# =====================================================================================
#                                       MAIN
# =====================================================================================

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
