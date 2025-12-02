# =========================
# Autofesa — AutoGen + FAISS + Gradio (Versión Optimizada)
# =========================

# ---- 1. Instalaciones ----
# Usamos faiss-cpu para asegurar compatibilidad en Colab estándar
!pip install -q faiss-cpu langchain-huggingface langchain-community autogen gradio

import os
import shutil
import pandas as pd
import nest_asyncio
import autogen
from typing import Annotated, Optional, List
from google.colab import userdata

# Componentes de LangChain / Vector Store
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

# UI
import gradio as gr

# Parche necesario para que AutoGen funcione dentro de Jupyter/Colab
nest_asyncio.apply()

# =========================
# 2. Configuración
# =========================
BASE_DIR = "/content"
CSV_FILENAME = "autofesa_completo_20251202_0932.csv" 
CSV_PATH = os.path.join(BASE_DIR, CSV_FILENAME)

# Gestión robusta de la API Key
try:
    GOOGLE_KEY = userdata.get('GOOGLE_API_KEY')
except Exception:
    GOOGLE_KEY = None

if not GOOGLE_KEY:
    GOOGLE_KEY = input("🔑 Introduce tu GOOGLE_API_KEY: ").strip()

if not GOOGLE_KEY:
    raise ValueError("❌ Error: Se necesita una API Key válida.")

# =========================
# 3. Carga y Vectorización
# =========================

def cargar_datos():
    """Carga el CSV o crea datos falsos si no existe."""
    if not os.path.exists(CSV_PATH):
        print(f"⚠️ Archivo {CSV_FILENAME} no encontrado. Generando datos de prueba...")
        return [
            Document(page_content="BMW Serie 3 320d. Color Blanco.", metadata={"Modelo": "BMW Serie 3", "Precio": 20000, "Km": 50000, "Link": "http://auto.com/1"}),
            Document(page_content="Audi A4 TDI. Color Negro.", metadata={"Modelo": "Audi A4", "Precio": 15000, "Km": 80000, "Link": "http://auto.com/2"}),
            Document(page_content="Ford Fiesta EcoBoost. Pequeño.", metadata={"Modelo": "Ford Fiesta", "Precio": 8000, "Km": 30000, "Link": "http://auto.com/3"})
        ]
    
    df = pd.read_csv(CSV_PATH)
    docs = []
    # Aseguramos columnas numéricas para evitar errores de filtrado después
    df['Precio'] = pd.to_numeric(df['Precio'], errors='coerce').fillna(0).astype(int)
    df['Km'] = pd.to_numeric(df['Km'], errors='coerce').fillna(0).astype(int)
    
    for _, row in df.iterrows():
        # Creamos un texto rico para la búsqueda semántica
        contenido = f"Coche: {row['Modelo']}. {row['Combustible']}. Año {row['Año']}."
        # Guardamos los datos exactos en metadatos para filtrado preciso
        meta = {
            "Modelo": row['Modelo'],
            "Precio": row['Precio'],
            "Km": row['Km'],
            "Link": row['Link']
        }
        docs.append(Document(page_content=contenido, metadata=meta))
    
    print(f"✅ {len(docs)} coches cargados y procesados.")
    return docs

print("⏳ Generando Embeddings y Base de Datos...")
docs = cargar_datos()
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectorstore = FAISS.from_documents(docs, embeddings)
print("✅ Sistema listo.")

# =========================
# 4. La Herramienta (The Tool)
# =========================

# MEJORA: Usamos Annotated y tipos nativos (int) para que el LLM entienda mejor
def tool_buscar_inventario(
    consulta: Annotated[str, "Descripción del coche que busca el usuario (ej: 'BMW deportivo')"],
    precio_max: Annotated[Optional[int], "Presupuesto máximo en euros. Usa None si no se especifica."] = None,
    km_max: Annotated[Optional[int], "Kilometraje máximo. Usa None si no se especifica."] = None
) -> str:
    """
    Busca coches semánticamente y luego filtra estrictamente por precio y km usando metadatos.
    """
    print(f"🔍 BUSCANDO: '{consulta}' | Max €: {precio_max} | Max Km: {km_max}")
    
    # 1. Búsqueda Semántica (Traemos los 20 más relevantes)
    results = vectorstore.similarity_search(consulta, k=20)
    
    if not results:
        return "No se encontraron resultados semánticos."

    filtrados = []
    
    # 2. Filtrado Lógico (Usando Metadatos, NO Regex)
    for doc in results:
        meta = doc.metadata
        precio_coche = meta.get("Precio", 9999999)
        km_coche = meta.get("Km", 9999999)
        
        # Lógica de filtro: Si el usuario puso límite, comprobamos. Si no, pasa.
        cumple_precio = (precio_max is None) or (precio_coche <= precio_max)
        cumple_km = (km_max is None) or (km_coche <= km_max)
        
        if cumple_precio and cumple_km:
            info = f"- {meta['Modelo']} | {precio_coche}€ | {km_coche}km | [Ver]({meta['Link']})"
            filtrados.append(info)
            
    if not filtrados:
        return f"Encontré coches tipo '{consulta}', pero ninguno por debajo de {precio_max}€ o {km_max}km."

    # Devolvemos solo los top 5 para no saturar al LLM
    return "Coches encontrados:\n" + "\n".join(filtrados[:5])

# =========================
# 5. Configuración Agentes AutoGen (CORREGIDO)
# =========================

llm_config = {
    "config_list": [{
        "model": "gemini-2.0-flash",
        "api_key": GOOGLE_KEY,
        "api_type": "google"
    }],
    "temperature": 0
}

# 1. EL PROXY (Tu ordenador)
# AUMENTAMOS max_consecutive_auto_reply a 5 para que le de tiempo a:
# Pensar -> Llamar Herramienta -> Ejecutar Herramienta -> Leer Resultado -> Responder
user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=5,  # <--- CAMBIO IMPORTANTE (Antes era 1)
    code_execution_config={"use_docker": False},
    # Criterio de parada: Si el agente dice "TERMINATE", paramos.
    is_termination_msg=lambda x: x.get("content", "") and "TERMINATE" in x.get("content", "")
)

# 2. EL AGENTE (Vendedor)
# Le decimos explícitamente que termine la conversación con TERMINATE cuando acabe.
sales_agent = autogen.AssistantAgent(
    name="vendedor",
    llm_config=llm_config,
    system_message="""Eres un vendedor experto de Autofesa.
    
    TU MISIÓN:
    1. Recibes una petición del usuario.
    2. SIEMPRE utiliza la herramienta 'buscar_inventario' inmediatamente. No hagas preguntas antes de buscar.
    3. Si la herramienta devuelve datos, resume los 3-5 mejores coches de forma atractiva (Modelo, Precio, Link).
    4. Si la herramienta no devuelve nada, dilo y sugiere cambiar filtros.
    5. AL FINAL DE TU RESPUESTA FINAL, escribe la palabra: TERMINATE
    """
)

# Registramos la función
autogen.register_function(
    tool_buscar_inventario,
    caller=sales_agent,
    executor=user_proxy,
    name="buscar_inventario",
    description="Busca en el inventario de coches."
)

# =========================
# 6. Interfaz Chat (Gradio)
# =========================

def chat_logic(mensaje, history):
    # Preparamos el historial visual para Gradio
    if history is None: history = []
    
    # AutoGen necesita un inicio claro.
    # Nota: initiate_chat reinicia el contexto del agente en cada turno en esta config simple.
    # Para mantener contexto real, se requiere gestionar el estado del agente (más complejo).
    try:
        chat_res = user_proxy.initiate_chat(
            sales_agent,
            message=mensaje,
            summary_method="last_msg"
        )
        respuesta = chat_res.summary
    except Exception as e:
        respuesta = f"Error: {str(e)}"

    history.append({"role": "user", "content": mensaje})
    history.append({"role": "assistant", "content": respuesta})
    
    return "", history # Limpia el input box y actualiza chat

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🤖 Autofesa AI Assistant")
    
    chatbot = gr.Chatbot(type="messages", height=450)
    msg = gr.Textbox(label="Escribe tu consulta...", placeholder="Busco un coche barato...")
    clear = gr.Button("Limpiar Chat")

    msg.submit(chat_logic, [msg, chatbot], [msg, chatbot])
    
    # Botón limpiar
    clear.click(lambda: None, None, chatbot, queue=False)

demo.launch(server_name="0.0.0.0", share=True, debug=True)