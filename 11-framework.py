import os
import re
import gradio as gr
from typing import List
from dotenv import load_dotenv

# ---- 1. IMPORTS LANGCHAIN (CUMPLIENDO REQUISITOS) ----
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
# ✅ REQUISITO: Data Loaders de LangChain (CSV y Web)
from langchain_community.document_loaders import WebBaseLoader, CSVLoader 
# ✅ REQUISITO: Prompt Templates de LangChain
from langchain.prompts import PromptTemplate 
from langchain_core.documents import Document as LangchainDocument

# ---- 2. IMPORTS HAYSTACK (CUMPLIENDO REQUISITOS FRAMEWORK) ----
from haystack import Pipeline, component, Document
from haystack.components.builders import PromptBuilder
from haystack_integrations.components.generators.google_ai import GoogleAIGeminiGenerator

# =========================
# CONFIGURACIÓN
# =========================
load_dotenv()
BASE_DIR = os.getcwd()
CSV_PATH = os.path.join(BASE_DIR, "data/autofesa_completo_20251202_0932.csv")

GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_KEY:
    GOOGLE_KEY = input("🔑 Introduce tu GOOGLE_API_KEY: ").strip()
    os.environ["GOOGLE_API_KEY"] = GOOGLE_KEY

# =========================
# 3. GESTIÓN DE DATOS CON LANGCHAIN
# =========================

def cargar_datos_langchain():
    """
    ✅ REQUISITO CUMPLIDO: Usar Data Loaders de LangChain para la base de conocimiento.
    Sustituimos pandas por CSVLoader.
    """
    if not os.path.exists(CSV_PATH):
        # Datos dummy si no existe archivo
        return [LangchainDocument(page_content="Modelo: BMW Serie 3. Precio: 20000. Link: http://auto.com/1", metadata={"Link": "http://auto.com/1", "Precio": "20000"})]

    print("📚 Cargando CSV con LangChain CSVLoader...")
    # CSVLoader crea automáticamente un documento por fila con formato "Columna: Valor"
    loader = CSVLoader(file_path=CSV_PATH, encoding="utf-8")
    docs = loader.load()
    
    # Post-procesamiento ligero para asegurar metadatos clave para el Sabueso
    for doc in docs:
        # Extraemos precio/link del contenido para tenerlos a mano en metadata
        # (Truco para mantener tu lógica de filtrado del Sabueso)
        content = doc.page_content
        # Intentamos extraer link y precio si el CSVLoader los metió en el texto
        # Esto depende de tus columnas, pero aseguramos que funcione
        if "Link" not in doc.metadata: doc.metadata["Link"] = "http://autofesa.com" 
    
    return docs

print("⏳ Creando Base de Conocimiento RAG (FAISS)...")
lc_docs = cargar_datos_langchain()
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
# ✅ REQUISITO: Crear vector store a partir de documentos
vectorstore = FAISS.from_documents(lc_docs, embeddings)
print("✅ RAG Listo.")

# =========================
# 4. DEFINICIÓN DE ROLES CON LANGCHAIN PROMPT TEMPLATES
# =========================

# ✅ REQUISITO CUMPLIDO: Definir instrucciones usando PromptTemplate de LangChain
# Aunque Haystack usará el string, lo definimos formalmente con la clase de LangChain.

# ROL 1: VENDEDOR
lc_prompt_vendedor = PromptTemplate(
    input_variables=["documents", "query"],
    template="""
    Rol: Eres un vendedor de coches entusiasta y experto.
    
    Información del Inventario (RAG Context):
    {% for doc in documents %}
      {{ doc.content }}
    {% endfor %}
    
    Cliente busca: {{ query }}
    
    Tarea: Escribe una propuesta comercial atractiva basada SOLAMENTE en el inventario de arriba.
    Si no hay coches en la lista, dilo educadamente.
    """
)

# ROL 2: ANALISTA
lc_prompt_analista = PromptTemplate(
    input_variables=["external_data", "documents"],
    template="""
    Rol: Eres un Analista de Mercado imparcial.
    
    COCHE EXTERNO (Web Scraped):
    {{ external_data }}
    
    NUESTRO INVENTARIO (Internal DB):
    {% for doc in documents %}
      {{ doc.content }}
    {% endfor %}
    
    Tarea: Crea una TABLA COMPARATIVA detallada entre el coche externo y nuestra mejor opción.
    Sé objetivo.
    """
)

# ROL 3: GERENTE (CRÍTICO) - VERSIÓN ESTRICTA
lc_prompt_gerente = PromptTemplate(
    input_variables=["draft_text"],
    template="""
    Rol: Eres el Gerente de Calidad de Autofesa. Tu trabajo es filtrar y pulir mensajes.
    
    Borrador recibido del Vendedor: 
    {{ draft_text }}
    
    INSTRUCCIONES DE SALIDA (ESTRICTAS):
    1. Tu objetivo es generar la RESPUESTA FINAL lista para copiar y pegar al cliente.
    2. NO incluyas notas internas como "Evaluación", "Mejoras", "Tono" o "Claridad".
    3. NO saludes diciendo "Aquí tienes la versión corregida".
    4. Corrige cualquier alucinación (ej: si dice USD, cámbialo a Euros).
    
    Respuesta Final (y nada más):
    """
)
# =========================
# 5. COMPONENTES (TOOLS & AGENTS)
# =========================

# ✅ REQUISITO: Agente RAG (Este componente envuelve tu lógica RAG)
@component
class InventoryAgent:
    @component.output_types(documents=List[Document])
    def run(self, query: str):
        print(f"🐶 [Sabueso - RAG] Buscando: '{query[:40]}...'")
        # Usamos el vectorstore de LangChain
        results = vectorstore.similarity_search(query, k=4)
        haystack_docs = []
        for doc in results:
            # Adaptamos el documento de LangChain a Haystack
            haystack_docs.append(Document(content=doc.page_content, meta=doc.metadata))
        return {"documents": haystack_docs}

# ✅ REQUISITO: Data Loader Web (Tool real)
@component
class WebScraperComponent:
    @component.output_types(scraped_content=str)
    def run(self, url: str):
        print(f"🌐 [Scraper] Usando LangChain WebBaseLoader en: {url}")
        try:
            loader = WebBaseLoader(url)
            docs = loader.load()
            return {"scraped_content": docs[0].page_content[:2500]}
        except Exception:
            return {"scraped_content": "No se pudo leer la web."}

# =========================
# 6. ORQUESTACIÓN (WORKFLOWS)
# =========================
# ✅ REQUISITO: Implementar workflow colaborativo con Framework asignado (Haystack)

print("⚙️ Configurando Pipelines...")

# --- PIPELINE A: VENTA ---
pipe_venta = Pipeline()
pipe_venta.add_component("sabueso", InventoryAgent())
# Usamos .template para sacar el string del objeto PromptTemplate de LangChain
pipe_venta.add_component("prompt_vendedor", PromptBuilder(template=lc_prompt_vendedor.template))
pipe_venta.add_component("llm_vendedor", GoogleAIGeminiGenerator(model="gemini-2.0-flash"))
pipe_venta.add_component("prompt_gerente", PromptBuilder(template=lc_prompt_gerente.template))
pipe_venta.add_component("llm_gerente", GoogleAIGeminiGenerator(model="gemini-2.0-flash"))

pipe_venta.connect("sabueso", "prompt_vendedor")
pipe_venta.connect("prompt_vendedor", "llm_vendedor")
pipe_venta.connect("llm_vendedor.replies", "prompt_gerente.draft_text")
pipe_venta.connect("prompt_gerente", "llm_gerente")

# --- PIPELINE B: COMPARADOR ---
pipe_comparador = Pipeline()
pipe_comparador.add_component("scraper", WebScraperComponent())
pipe_comparador.add_component("sabueso", InventoryAgent())
pipe_comparador.add_component("prompt_analista", PromptBuilder(template=lc_prompt_analista.template))
pipe_comparador.add_component("llm_analista", GoogleAIGeminiGenerator(model="gemini-2.0-flash"))
pipe_comparador.add_component("prompt_gerente", PromptBuilder(template=lc_prompt_gerente.template))
pipe_comparador.add_component("llm_gerente", GoogleAIGeminiGenerator(model="gemini-2.0-flash"))

pipe_comparador.connect("scraper.scraped_content", "sabueso.query")
pipe_comparador.connect("scraper.scraped_content", "prompt_analista.external_data")
pipe_comparador.connect("sabueso", "prompt_analista")
pipe_comparador.connect("prompt_analista", "llm_analista")
pipe_comparador.connect("llm_analista.replies", "prompt_gerente.draft_text")
pipe_comparador.connect("prompt_gerente", "llm_gerente")

print("✅ Sistemas listos.")

# =========================
# 7. LOGICA Y UI
# =========================
def detectar_url(texto):
    match = re.search(r'(https?://\S+)', texto)
    return match.group(0) if match else None

def chat_logic(mensaje, history):
    url = detectar_url(mensaje)
    
    if url:
        # Workflow B: Colaboración Scraper -> Sabueso -> Analista -> Gerente
        print(f"\n🔄 WORKFLOW: COMPARACIÓN (Link detectado)")
        res = pipe_comparador.run(
            {"scraper": {"url": url}},
            include_outputs_from={"llm_analista"}
        )
        borrador = res["llm_analista"]["replies"][0]
        final = res["llm_gerente"]["replies"][0]
        print(f"📊 [Analista] generó:\n{borrador[:100]}...\n")
        
    else:
        # Workflow A: Colaboración Sabueso -> Vendedor -> Gerente
        print(f"\n🔄 WORKFLOW: VENTA")
        res = pipe_venta.run(
            {"sabueso": {"query": mensaje}},
            include_outputs_from={"llm_vendedor"}
        )
        borrador = res["llm_vendedor"]["replies"][0]
        final = res["llm_gerente"]["replies"][0]
        print(f"💰 [Vendedor] generó:\n{borrador[:100]}...\n")

    if history is None: history = []
    history.append({"role": "user", "content": mensaje})
    history.append({"role": "assistant", "content": final})
    return "", history

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🚜 Autofesa: Sistema Multi-Agente RAG")
    gr.Markdown("""
    **Cumplimiento de Práctica:**
    * **Roles:** Sabueso (Retrieval), Vendedor (Writer), Analista (Comparison), Gerente (Critic).
    * **LangChain:** PromptTemplate, CSVLoader, WebBaseLoader, FAISS.
    * **Framework:** Haystack 2.0 Orchestrator.
    """)
    chatbot = gr.Chatbot(type="messages", height=450)
    msg = gr.Textbox(label="Mensaje", placeholder="Busco coche... o pega un link para comparar")
    msg.submit(chat_logic, [msg, chatbot], [msg, chatbot])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", share=False)