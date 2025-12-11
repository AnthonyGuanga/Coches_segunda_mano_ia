import os
import re
import pandas as pd
import gradio as gr
from typing import List, Optional
from dotenv import load_dotenv

# ---- IMPORTS LANGCHAIN ----
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document as LangchainDocument
from langchain_community.document_loaders import WebBaseLoader # <--- NUEVO IMPORT

# ---- IMPORTS HAYSTACK ----
from haystack import Pipeline, component, Document
from haystack.components.builders import PromptBuilder
from haystack_integrations.components.generators.google_ai import GoogleAIGeminiGenerator

# =========================
# 1. CONFIGURACIÓN
# =========================
load_dotenv()
BASE_DIR = os.getcwd()
CSV_PATH = os.path.join(BASE_DIR, "autofesa_completo_20251202_0932.csv")

GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_KEY:
    GOOGLE_KEY = input("🔑 Introduce tu GOOGLE_API_KEY: ").strip()
    os.environ["GOOGLE_API_KEY"] = GOOGLE_KEY

# =========================
# 2. CARGA DE DATOS (Igual que antes)
# =========================
def cargar_datos_langchain():
    if not os.path.exists(CSV_PATH):
        return [
            LangchainDocument(page_content="BMW Serie 3 320d. Diesel. 190cv.", metadata={"Modelo": "BMW Serie 3", "Precio": 20000, "Km": 50000, "Link": "http://auto.com/1"}),
            LangchainDocument(page_content="Audi A4 TDI. Diesel. 150cv.", metadata={"Modelo": "Audi A4", "Precio": 15000, "Km": 80000, "Link": "http://auto.com/2"}),
        ]
    df = pd.read_csv(CSV_PATH)
    docs = []
    df['Precio'] = pd.to_numeric(df['Precio'], errors='coerce').fillna(0).astype(int)
    df['Km'] = pd.to_numeric(df['Km'], errors='coerce').fillna(0).astype(int)
    for _, row in df.iterrows():
        contenido = f"{row['Modelo']}. {row['Combustible']}."
        meta = {"Modelo": row['Modelo'], "Precio": row['Precio'], "Km": row['Km'], "Link": row['Link']}
        docs.append(LangchainDocument(page_content=contenido, metadata=meta))
    return docs

print("⏳ Indexando inventario...")
lc_docs = cargar_datos_langchain()
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectorstore = FAISS.from_documents(lc_docs, embeddings)
print("✅ Base de datos lista.")

# =========================
# 3. COMPONENTES DEL SISTEMA
# =========================

# --- AGENTE 1: EL SABUESO (Busca en nuestra DB) ---
@component
class InventoryAgent:
    @component.output_types(documents=List[Document])
    def run(self, query: str):
        print(f"🐶 [Sabueso] Buscando coches similares a: '{query[:50]}...'")
        results = vectorstore.similarity_search(query, k=4)
        haystack_docs = []
        for doc in results:
            meta = doc.metadata
            txt = f"NUESTRO COCHE: {meta['Modelo']} | {meta['Precio']}€ | {meta['Km']}km"
            haystack_docs.append(Document(content=txt, meta=meta))
        return {"documents": haystack_docs}

# --- NUEVO COMPONENTE: EL SCRAPER (Web Loader) ---
@component
class WebScraperComponent:
    """Usa LangChain WebBaseLoader para leer una URL externa."""
    @component.output_types(scraped_content=str, status=str)
    def run(self, url: str):
        print(f"🌐 [Scraper] Descargando info de: {url}")
        try:
            loader = WebBaseLoader(url)
            # Cargamos y limitamos caracteres para no saturar al LLM
            docs = loader.load()
            content = docs[0].page_content[:2000] # Solo los primeros 2000 caracteres
            # Limpieza básica de saltos de línea
            content = " ".join(content.split())
            return {"scraped_content": content, "status": "ok"}
        except Exception as e:
            return {"scraped_content": "", "status": f"Error: {str(e)}"}

# =========================
# 4. DEFINICIÓN DE AGENTES LLM
# =========================

# --- AGENTE 2: EL VENDEDOR (Modo Normal) ---
template_vendedor = """
Rol: Eres un vendedor de coches entusiasta.
Inventario:
{% for doc in documents %}
  {{ doc.content }}
{% endfor %}
Cliente: {{ query }}
Escribe una propuesta corta y persuasiva.
"""

# --- AGENTE 4 (NUEVO): EL ANALISTA (Modo Comparación) ---
# Este agente recibe el texto de la web externa + nuestros coches
template_analista = """
Rol: Eres un Analista de Mercado imparcial.
Tarea: Comparar el coche externo que está mirando el cliente con nuestras opciones.

COCHE EXTERNO (Encontrado en la web):
{{ external_data }}

NUESTRO INVENTARIO (Alternativas):
{% for doc in documents %}
  {{ doc.content }}
{% endfor %}

Instrucciones:
1. Analiza las caracteristicas del coche externo.
2. Crea una TABLA COMPARATIVA comparándolo con nuestro mejor candidato.
3. Argumenta por qué nuestra opción es mejor (precio, garantía, confianza) o si la suya es buena.
4. Sé profesional y analítico.

Análisis del experto:
"""

# --- AGENTE 3: EL GERENTE (Validador Común) ---
template_gerente = """
Rol: Gerente de Calidad.
Tarea: Revisar el texto generado y darle formato final al cliente.

Texto Generado: {{ draft_text }}

Tu respuesta final al cliente (limpia y educada):
"""

# =========================
# 5. PIPELINES (FLUJOS DE TRABAJO)
# =========================

print("⚙️ Configurando Agentes...")

# --- PIPELINE A: VENTA NORMAL ---
pipe_venta = Pipeline()

# Instanciamos los componentes DENTRO del add_component para que sean únicos
pipe_venta.add_component("sabueso", InventoryAgent()) 
pipe_venta.add_component("prompt_vendedor", PromptBuilder(template=template_vendedor))
pipe_venta.add_component("llm_vendedor", GoogleAIGeminiGenerator(model="gemini-2.0-flash")) # Instancia única 1
pipe_venta.add_component("prompt_gerente", PromptBuilder(template=template_gerente))
pipe_venta.add_component("llm_gerente", GoogleAIGeminiGenerator(model="gemini-2.0-flash"))  # Instancia única 2

# Conexiones Venta
pipe_venta.connect("sabueso", "prompt_vendedor")
pipe_venta.connect("prompt_vendedor", "llm_vendedor")
pipe_venta.connect("llm_vendedor.replies", "prompt_gerente.draft_text")
pipe_venta.connect("prompt_gerente", "llm_gerente")


# --- PIPELINE B: COMPARADOR (NUEVO) ---
pipe_comparador = Pipeline()

pipe_comparador.add_component("scraper", WebScraperComponent())
# IMPORTANTE: Creamos un NUEVO InventoryAgent para este pipeline (no se pueden compartir)
pipe_comparador.add_component("sabueso", InventoryAgent()) 
pipe_comparador.add_component("prompt_analista", PromptBuilder(template=template_analista))
pipe_comparador.add_component("llm_analista", GoogleAIGeminiGenerator(model="gemini-2.0-flash")) # Instancia única 3
pipe_comparador.add_component("prompt_gerente", PromptBuilder(template=template_gerente))
pipe_comparador.add_component("llm_gerente", GoogleAIGeminiGenerator(model="gemini-2.0-flash")) # Instancia única 4

# Conexiones Comparador
# 1. El texto scrapeado va al Sabueso (para buscar coches similares) y al Analista
pipe_comparador.connect("scraper.scraped_content", "sabueso.query")
pipe_comparador.connect("scraper.scraped_content", "prompt_analista.external_data")

# 2. Los coches encontrados por el sabueso van al analista
pipe_comparador.connect("sabueso", "prompt_analista")

# 3. Flujo LLM
pipe_comparador.connect("prompt_analista", "llm_analista")
pipe_comparador.connect("llm_analista.replies", "prompt_gerente.draft_text")
pipe_comparador.connect("prompt_gerente", "llm_gerente")

print("✅ Pipelines listos: [A: Venta Normal] y [B: Comparador Web]")

# =========================
# 6. LÓGICA DE CONTROL
# =========================

def detectar_url(texto):
    # Regex simple para encontrar URLs
    url_pattern = re.compile(r'(https?://\S+)')
    match = url_pattern.search(texto)
    return match.group(0) if match else None

def chat_logic(mensaje, history):
    url_encontrada = detectar_url(mensaje)
    
    # --- MODO COMPARADOR (Si hay URL) ---
    if url_encontrada:
        print(f"\n🚨 URL DETECTADA: Activando Agente Analista ({url_encontrada})")
        res = pipe_comparador.run(
            {
                "scraper": {"url": url_encontrada},
                # El prompt gerente necesita el texto, que le llega del analista, 
                # pero Haystack a veces pide inicialización vacía si es compleja
            },
            include_outputs_from={"llm_analista"}
        )
        borrador = res["llm_analista"]["replies"][0]
        final = res["llm_gerente"]["replies"][0]
        
        print(f"\n📊 [ANALISTA] Borrador Comparativo:\n{borrador}\n")
        
    # --- MODO VENTA (Si es texto normal) ---
    else:
        print(f"\n💬 TEXTO NORMAL: Activando Agente Vendedor")
        res = pipe_venta.run(
            {"sabueso": {"query": mensaje}},
            include_outputs_from={"llm_vendedor"}
        )
        borrador = res["llm_vendedor"]["replies"][0]
        final = res["llm_gerente"]["replies"][0]
        
        print(f"\n💰 [VENDEDOR] Borrador de Venta:\n{borrador}\n")

    print(f"✅ [GERENTE] Aprobado.")

    if history is None: history = []
    history.append({"role": "user", "content": mensaje})
    history.append({"role": "assistant", "content": final})
    return "", history

# =========================
# 7. INTERFAZ GRÁFICA (Visualización de Workflows)
# =========================

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🤖 Autofesa: Sistema Multi-Agente Híbrido")
    
    # Explicación visual para tu práctica
    gr.Markdown("""
    ### 🔀 Arquitectura de Agentes Dinámica
    El sistema detecta automáticamente la intención del usuario y activa el pipeline correspondiente:

    | Input del Usuario | Modo Activo | Flujo de Agentes (Workflow) |
    | :--- | :--- | :--- |
    | **Texto Normal** <br> *(ej: "Busco un BMW barato")* | **💰 MODO VENTA** | 🐶 **Sabueso** (Data) → 👨‍💼 **Vendedor** (Creativo) → 🧐 **Gerente** (Validador) |
    | **Enlace URL** <br> *(ej: "Mira este coche: https://...")* | **📊 MODO ANALISTA** | 🌐 **Scraper** (Web) → 🐶 **Sabueso** (Contexto) → 📊 **Analista** (Comparador) → 🧐 **Gerente** (Validador) |
    """)
    
    # Componentes del Chat
    chatbot = gr.Chatbot(type="messages", height=450, label="Historial de Conversación")
    msg = gr.Textbox(
        label="Tu Mensaje", 
        placeholder="Escribe 'Busco un Audi' o pega un enlace para comparar..."
    )
    
    # Botones adicionales para limpiar
    with gr.Row():
        btn_send = gr.Button("Enviar", variant="primary")
        btn_clear = gr.Button("Limpiar Chat")

    # Eventos
    # Enter presionado
    msg.submit(chat_logic, [msg, chatbot], [msg, chatbot])
    # Botón enviar clickeado
    btn_send.click(chat_logic, [msg, chatbot], [msg, chatbot])
    # Botón limpiar
    btn_clear.click(lambda: None, None, chatbot, queue=False)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", share=False)