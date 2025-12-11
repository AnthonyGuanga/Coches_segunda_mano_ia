import os
import pandas as pd
import gradio as gr
from typing import List, Optional
from dotenv import load_dotenv

# ---- 1. IMPORTS DE LANGCHAIN (Lógica RAG original) ----
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document as LangchainDocument
# Import solicitado explícitamente, aunque usaremos la lógica manual para mantener el filtrado exacto
from langchain.chains import RetrievalQA 

# ---- 2. IMPORTS DE HAYSTACK (El Orquestador) ----
from haystack import Pipeline, component, Document
from haystack.components.builders import PromptBuilder
from haystack_integrations.components.generators.google_ai import GoogleAIGeminiGenerator

# =========================
# CONFIGURACIÓN
# =========================
load_dotenv() # Carga .env si existe

BASE_DIR = os.getcwd()
CSV_FILENAME = "data/autofesa_completo_20251202_0932.csv"
CSV_PATH = os.path.join(BASE_DIR, CSV_FILENAME)

# API KEY
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_KEY:
    GOOGLE_KEY = input("🔑 Introduce tu GOOGLE_API_KEY: ").strip()
    os.environ["GOOGLE_API_KEY"] = GOOGLE_KEY

# =========================
# 3. LÓGICA LANGCHAIN (Carga y Vector Store)
# =========================
# Esta parte es IDÉNTICA a tu código anterior para mantener la consistencia

def cargar_datos_langchain():
    """Carga datos y retorna documentos formato LangChain."""
    if not os.path.exists(CSV_PATH):
        print(f"⚠️ Archivo {CSV_FILENAME} no encontrado. Generando datos de prueba...")
        return [
            LangchainDocument(page_content="BMW Serie 3 320d. Color Blanco.", metadata={"Modelo": "BMW Serie 3", "Precio": 20000, "Km": 50000, "Link": "http://auto.com/1"}),
            LangchainDocument(page_content="Audi A4 TDI. Color Negro.", metadata={"Modelo": "Audi A4", "Precio": 15000, "Km": 80000, "Link": "http://auto.com/2"}),
            LangchainDocument(page_content="Ford Fiesta EcoBoost. Pequeño.", metadata={"Modelo": "Ford Fiesta", "Precio": 8000, "Km": 30000, "Link": "http://auto.com/3"})
        ]

    df = pd.read_csv(CSV_PATH)
    docs = []
    # Limpieza
    df['Precio'] = pd.to_numeric(df['Precio'], errors='coerce').fillna(0).astype(int)
    df['Km'] = pd.to_numeric(df['Km'], errors='coerce').fillna(0).astype(int)

    for _, row in df.iterrows():
        contenido = f"Coche: {row['Modelo']}. {row['Combustible']}. Año {row['Año']}."
        meta = {
            "Modelo": row['Modelo'],
            "Precio": row['Precio'],
            "Km": row['Km'],
            "Link": row['Link']
        }
        docs.append(LangchainDocument(page_content=contenido, metadata=meta))
    
    return docs

print("⏳ Iniciando LangChain FAISS + HuggingFace...")
lc_docs = cargar_datos_langchain()
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
# Creamos la base de datos FAISS con LangChain
vectorstore = FAISS.from_documents(lc_docs, embeddings)
print("✅ VectorStore LangChain listo.")

# =========================
# 4. COMPONENTE PUENTE (Haystack Wrapper)
# =========================
# Aquí es donde Haystack toma el control usando la lógica de LangChain dentro

@component
class LangChainFAISSRetriever:
    """
    Componente personalizado de Haystack que usa FAISS de LangChain internamente.
    Replica tu lógica exacta de filtrado por Precio y Km.
    """
    
    @component.output_types(documents=List[Document])
    def run(self, query: str, precio_max: Optional[int] = None, km_max: Optional[int] = None):
        print(f"🔍 Búsqueda LangChain: '{query}' | Max €: {precio_max} | Max Km: {km_max}")
        
        # 1. Búsqueda semántica usando el vectorstore de LangChain
        results = vectorstore.similarity_search(query, k=20)
        
        haystack_docs = []
        
        # 2. Filtrado Lógico (Tu lógica original de Python)
        for doc in results:
            meta = doc.metadata
            precio_coche = meta.get("Precio", 9999999)
            km_coche = meta.get("Km", 9999999)

            cumple_precio = (precio_max is None) or (precio_coche <= precio_max)
            cumple_km = (km_max is None) or (km_coche <= km_max)

            if cumple_precio and cumple_km:
                # Convertimos documento de LangChain -> Documento de Haystack
                contenido_final = f"- {meta['Modelo']} | {precio_coche}€ | {km_coche}km | [Ver]({meta['Link']})"
                haystack_docs.append(Document(content=contenido_final, meta=meta))
        
        # Limitamos a 5 para no saturar contexto
        return {"documents": haystack_docs[:5]}

# =========================
# 5. ORQUESTACIÓN CON HAYSTACK
# =========================

# Instanciamos el componente personalizado
hybrid_retriever = LangChainFAISSRetriever()

# Prompt Template para el vendedor
template = """
Eres un vendedor experto de Autofesa.
Utiliza la siguiente lista de coches encontrados en el inventario para responder al usuario.
Si la lista está vacía, di que no hay coincidencias con esos filtros.

Inventario Encontrado:
{% for doc in documents %}
    {{ doc.content }}
{% endfor %}

Pregunta del usuario: {{ query }}

Respuesta útil y vendedora:
"""
prompt_builder = PromptBuilder(template=template)

# Generador Gemini
generator = GoogleAIGeminiGenerator(model="gemini-2.0-flash")

# --- CONSTRUCCIÓN DEL PIPELINE ---
pipeline = Pipeline()
pipeline.add_component("retriever", hybrid_retriever)
pipeline.add_component("prompt", prompt_builder)
pipeline.add_component("llm", generator)

# Conectamos: El output del retriever va al prompt, y el prompt al LLM
pipeline.connect("retriever.documents", "prompt.documents")
pipeline.connect("prompt", "llm")

print("✅ Pipeline Haystack (con cerebro LangChain) listo.")

# =========================
# 6. INTERFAZ GRADIO
# =========================

def extraer_filtros_basicos(mensaje):
    """
    Extracción muy simple de números para simular la detección de parámetros.
    En un sistema real, usarías un LLM router para extraer estos JSONs.
    Aquí lo dejo simple para que funcione rápido.
    """
    import re
    precio = None
    km = None
    
    # Busca patrones simples como "20000 euros" o "50000 km"
    match_precio = re.search(r'(\d+)\s*(?:€|euros|euro)', mensaje.lower())
    match_km = re.search(r'(\d+)\s*(?:km|kilómetros)', mensaje.lower())
    
    if match_precio: precio = int(match_precio.group(1))
    if match_km: km = int(match_km.group(1))
    
    return precio, km

def chat_logic(mensaje, history):
    if not mensaje: return "", history or []
    
    # 1. Extraer filtros (Lógica simple auxiliar)
    p_max, k_max = extraer_filtros_basicos(mensaje)
    
    # 2. Ejecutar Pipeline de Haystack
    # Pasamos la query y los filtros al componente retriever
    resultado = pipeline.run({
        "retriever": {
            "query": mensaje, 
            "precio_max": p_max, 
            "km_max": k_max
        },
        "prompt": {
            "query": mensaje
        }
    })
    
    respuesta = resultado["llm"]["replies"][0]
    
    if history is None: history = []
    history.append({"role": "user", "content": mensaje})
    history.append({"role": "assistant", "content": respuesta})
    
    return "", history

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🚜 Autofesa: Haystack Orchestrator + LangChain RAG")
    
    chatbot = gr.Chatbot(type="messages", height=450)
    msg = gr.Textbox(label="Consulta", placeholder="Busco BMW por menos de 25000 euros...")
    clear = gr.Button("Limpiar")
    
    msg.submit(chat_logic, [msg, chatbot], [msg, chatbot])
    clear.click(lambda: None, None, chatbot, queue=False)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", share=False)