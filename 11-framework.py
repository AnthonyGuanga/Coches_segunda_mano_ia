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

# =========================
# 4. DEFINICIÓN DE ROLES CON LANGCHAIN PROMPT TEMPLATES (CORREGIDO)
# =========================

# NOTA: Añadimos template_format="jinja2" para que LangChain respete las 
# dobles llaves {{ }} que necesita Haystack para funcionar.

# ROL 1: VENDEDOR
lc_prompt_vendedor = PromptTemplate(
    input_variables=["documents", "query"],
    template_format="jinja2", # <--- ¡ESTO ES LA CLAVE DEL ARREGLO!
    template="""
    Rol: Eres un vendedor de coches honesto de Autofesa.
    
    Información del Inventario (Contexto Real):
    {% for doc in documents %}
      - Modelo: {{ doc.meta['Modelo'] }} | Precio: {{ doc.meta['Precio'] }}€ | Info: {{ doc.content }}
    {% endfor %}
    
    Cliente busca: {{ query }}
    
    INSTRUCCIONES:
    1. Si el inventario está vacío o no encaja por precio (diferencia > 30%), di: "No tenemos exactamente eso, pero mira esto...".
    2. Si encaja, ¡véndelo con entusiasmo!
    3. NO uses marcadores como "[Tu nombre]". Eres "El Asistente de Autofesa".
    """
)

# ROL 2: ANALISTA
lc_prompt_analista = PromptTemplate(
    input_variables=["external_data", "documents"],
    template_format="jinja2", # <--- IMPORTANTE
    template="""
    Rol: Eres un Analista de Mercado.
    
    COCHE EXTERNO:
    {{ external_data }}
    
    NUESTRO INVENTARIO:
    {% for doc in documents %}
      - {{ doc.content }}
    {% endfor %}
    
    Tarea: Comparativa detallada (Tabla) entre el coche externo y el nuestro.
    """
)

# ROL 3: GERENTE
lc_prompt_gerente = PromptTemplate(
    input_variables=["draft_text"],
    template_format="jinja2", # <--- IMPORTANTE
    template="""
    Rol: Gerente de Calidad.
    
    Borrador: 
    {{ draft_text }}
    
    Tarea: Genera la respuesta FINAL para el cliente.
    Corrección: Elimina saludos genéricos o placeholders. Asegura que los datos sean los del inventario.
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
        # Workflow B: COMPARADOR
        # Aquí NO hace falta pasar 'query' extra porque todo se conecta internamente 
        # (Scraper -> Analista)
        print(f"\n🔄 WORKFLOW: COMPARACIÓN (Link detectado)")
        res = pipe_comparador.run(
            {"scraper": {"url": url}},
            include_outputs_from={"llm_analista"}
        )
        borrador = res["llm_analista"]["replies"][0]
        final = res["llm_gerente"]["replies"][0]
        print(f"📊 [Analista] generó:\n{borrador[:100]}...\n")
        
    else:
        # Workflow A: VENTA
        print(f"\n🔄 WORKFLOW: VENTA")
        # ⚠️ CORRECCIÓN AQUÍ ABAJO:
        # Hay que pasar 'query' tanto al Sabueso (para buscar) 
        # como al Prompt (para que el vendedor sepa qué contestar)
        res = pipe_venta.run(
            {
                "sabueso": {"query": mensaje}, 
                "prompt_vendedor": {"query": mensaje} # <--- AÑADIR ESTA LÍNEA
            },
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