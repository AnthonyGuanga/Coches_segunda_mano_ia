import os
import pandas as pd
import gradio as gr
from typing import List, Optional
from dotenv import load_dotenv

# ---- IMPORTS LANGCHAIN (Base de Datos) ----
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document as LangchainDocument

# ---- IMPORTS HAYSTACK (Orquestador Multi-Agente) ----
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
# 2. LÓGICA DE DATOS (LangChain + FAISS)
# =========================
def cargar_datos_langchain():
    if not os.path.exists(CSV_PATH):
        # Datos Dummy si no hay CSV
        return [
            LangchainDocument(page_content="BMW Serie 3. Diesel.", metadata={"Modelo": "BMW Serie 3", "Precio": 20000, "Km": 50000, "Link": "http://auto.com/1"}),
            LangchainDocument(page_content="Audi A4. Gasolina.", metadata={"Modelo": "Audi A4", "Precio": 15000, "Km": 80000, "Link": "http://auto.com/2"}),
        ]
    
    df = pd.read_csv(CSV_PATH)
    docs = []
    # Conversión numérica segura
    df['Precio'] = pd.to_numeric(df['Precio'], errors='coerce').fillna(0).astype(int)
    df['Km'] = pd.to_numeric(df['Km'], errors='coerce').fillna(0).astype(int)

    for _, row in df.iterrows():
        contenido = f"{row['Modelo']}. {row['Combustible']}."
        meta = {"Modelo": row['Modelo'], "Precio": row['Precio'], "Km": row['Km'], "Link": row['Link']}
        docs.append(LangchainDocument(page_content=contenido, metadata=meta))
    return docs

print("⏳ Agente 1 (Sabueso): Indexando inventario...")
lc_docs = cargar_datos_langchain()
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectorstore = FAISS.from_documents(lc_docs, embeddings)
print("✅ Agente 1 listo.")

# =========================
# 3. COMPONENTES DEL SISTEMA MULTI-AGENTE
# =========================

# --- AGENTE 1: EL SABUESO (Retrieval Tool) ---
@component
class InventoryAgent:
    """Busca y filtra datos técnicos estrictos."""
    
    @component.output_types(documents=List[Document])
    def run(self, query: str, precio_max: Optional[int] = None, km_max: Optional[int] = None):
        print(f"🐶 [Agente Sabueso] Buscando: {query} (Max €{precio_max})")
        results = vectorstore.similarity_search(query, k=15)
        haystack_docs = []
        
        for doc in results:
            meta = doc.metadata
            p = meta.get("Precio", 999999)
            k = meta.get("Km", 999999)
            
            if (precio_max is None or p <= precio_max) and (km_max is None or k <= km_max):
                # Formato claro para que los siguientes agentes lean bien
                txt = f"VEHÍCULO: {meta['Modelo']} | PRECIO: {p}€ | KM: {k} | REF: {meta['Link']}"
                haystack_docs.append(Document(content=txt, meta=meta))
        
        return {"documents": haystack_docs[:4]} # Solo los 4 mejores

# --- AGENTE 2: EL VENDEDOR (Writer) ---
template_vendedor = """
Rol: Eres "El Vendedor", un experto comercial de coches.
Tarea: Escribe un borrador de respuesta para el cliente basado en los coches encontrados.
Tono: Entusiasta, persuasivo y enfocado en beneficios.

Coches disponibles (Datos Reales):
{% for doc in documents %}
  {{ doc.content }}
{% endfor %}

Cliente busca: {{ query }}

Instrucciones:
1. Si no hay coches, discúlpate.
2. Si hay coches, elige el mejor y "véndelo" con emoción. Menciona los otros brevemente.
3. NO inventes datos. Usa solo la lista de arriba.

Borrador del Vendedor:
"""

# --- AGENTE 3: EL GERENTE (Critic/Manager) ---
template_gerente = """
Rol: Eres "El Gerente", supervisor de calidad de Autofesa.
Tarea: Revisar y pulir el borrador del Vendedor.

Contexto Original (Datos Técnicos):
{% for doc in documents %}
  {{ doc.content }}
{% endfor %}

Borrador del Vendedor:
{{ sales_draft[0] }}

Instrucciones de Revisión:
1. VERIFICACIÓN DE HECHOS: Asegúrate de que el precio y modelo coincidan exactamente con el Contexto Original. Si el vendedor inventó algo, corrígelo.
2. FORMATO: Organiza la respuesta limpia, usa viñetas para los coches.
3. CIERRE: Asegúrate de que termine con una llamada a la acción clara (ej: "¿Te agendo una cita?").
4. Elimina cualquier texto interno como "Aquí tienes el borrador". Solo entrega el mensaje final para el cliente.

Respuesta Final Aprobada:
"""

# =========================
# 4. CONSTRUCCIÓN DEL WORKFLOW (PIPELINE)
# =========================

# Instanciamos componentes
agente_sabueso = InventoryAgent()

# Prompt + LLM para Agente Vendedor
prompt_vendedor = PromptBuilder(template=template_vendedor)
llm_vendedor = GoogleAIGeminiGenerator(model="gemini-2.0-flash")

# Prompt + LLM para Agente Gerente
prompt_gerente = PromptBuilder(template=template_gerente)
llm_gerente = GoogleAIGeminiGenerator(model="gemini-2.0-flash")

# Creamos el Pipeline Lineal
pipeline = Pipeline()

# Fase 1: Búsqueda
pipeline.add_component("sabueso", agente_sabueso)

# Fase 2: Redacción (Vendedor)
pipeline.add_component("prompt_vendedor", prompt_vendedor)
pipeline.add_component("llm_vendedor", llm_vendedor)

# Fase 3: Validación (Gerente)
pipeline.add_component("prompt_gerente", prompt_gerente)
pipeline.add_component("llm_gerente", llm_gerente)

# --- CONEXIONES ---
# 1. Sabueso -> Prompt Vendedor (Pasa los documentos)
pipeline.connect("sabueso.documents", "prompt_vendedor.documents")
# 2. Prompt Vendedor -> LLM Vendedor
pipeline.connect("prompt_vendedor", "llm_vendedor")

# 3. CRÍTICO: Necesita ver los documentos originales Y el borrador del vendedor
pipeline.connect("sabueso.documents", "prompt_gerente.documents") # Para chequear la verdad
pipeline.connect("llm_vendedor.replies", "prompt_gerente.sales_draft") # Para corregir el texto

# 4. Prompt Gerente -> LLM Gerente (Salida Final)
pipeline.connect("prompt_gerente", "llm_gerente")

print("✅ Sistema Multi-Agente (Sabueso -> Vendedor -> Gerente) Listo.")

# =========================
# 5. INTERFAZ
# =========================

def procesar_consulta(mensaje, history):
    # 1. Extracción de filtros
    import re
    precio, km = None, None
    m_p = re.search(r'(\d+)\s*(?:€|euros)', mensaje.lower())
    m_k = re.search(r'(\d+)\s*(?:km)', mensaje.lower())
    if m_p: precio = int(m_p.group(1))
    if m_k: km = int(m_k.group(1))

    # 2. Ejecución del Workflow
    # AQUI ESTA LA CORRECCION CLAVE: 'include_outputs_from'
    resultado = pipeline.run(
        {
            "sabueso": {"query": mensaje, "precio_max": precio, "km_max": km},
            "prompt_vendedor": {"query": mensaje}, 
        },
        include_outputs_from={"llm_vendedor"}  # <--- ESTO SOLUCIONA TU ERROR
    )

    # 3. EXTRAEMOS LA INFORMACIÓN INTERNA
    # Ahora sí existirá 'llm_vendedor' en el diccionario
    borrador_vendedor = resultado["llm_vendedor"]["replies"][0]
    
    # La salida final siempre viene por defecto
    respuesta_final = resultado["llm_gerente"]["replies"][0]

    # 4. IMPRIMIMOS EL DEBATE EN LA TERMINAL
    print("\n" + "="*50)
    print(f"🤖 AGENTE 2 (VENDEDOR) generó este borrador:")
    print("-" * 20)
    print(borrador_vendedor)
    print("="*50)
    
    print(f"🧐 AGENTE 3 (GERENTE) corrigió y aprobó:")
    print("-" * 20)
    print(respuesta_final)
    print("="*50 + "\n")

    # 5. Enviamos solo la versión final al chat web
    if history is None: history = []
    history.append({"role": "user", "content": mensaje})
    history.append({"role": "assistant", "content": respuesta_final})
    return "", history

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🤖 Autofesa Multi-Agent System")
    gr.Markdown("""
    **Workflow Activo:**
    1. 🐶 **Sabueso:** Busca en base de datos FAISS.
    2. 👨‍💼 **Vendedor:** Redacta borrador persuasivo.
    3. 🧐 **Gerente:** Valida datos y aprueba respuesta final.
    """)
    
    chatbot = gr.Chatbot(type="messages", height=450)
    msg = gr.Textbox(label="Consulta", placeholder="Busco un coche familiar por menos de 15000 euros...")
    msg.submit(procesar_consulta, [msg, chatbot], [msg, chatbot])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", share=False)