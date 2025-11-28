import os
import re 
import pandas as pd
from typing import Optional, List, Dict 
from datetime import datetime

# Importaciones de LangChain
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_core.documents import Document 
from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain_core.prompts import PromptTemplate 
from langchain_google_genai import ChatGoogleGenerativeAI

# =========================================================================
# === CONFIGURACIÓN GLOBAL Y GESTIÓN DE RUTAS ===
# =========================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db") 
COLLECTION_NAME = "inventario_coches_autofesa"

# 2. Configuración de Archivos
NOMBRE_ARCHIVO_CSV = os.path.join(BASE_DIR, "autofesa_completo_20251127_1029.csv") 

# 3. Configuración del LLM
# ⚠️ IMPORTANTE: Asegúrate de que esta clave sea válida o usa os.getenv()
LLM_API_KEY_MANUAL = "AIzaSyA6JVn8W47K6kuqvb1QqxZ512x15s50AOo" 
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash", 
    temperature=0,
    google_api_key=LLM_API_KEY_MANUAL 
)

# =========================================================================
# === BLOQUE 1: CARGAR Y TRANSFORMAR DATOS ===
# =========================================================================

def crear_documentos_desde_csv(nombre_archivo: str) -> list[Document]:
    """Carga el CSV y convierte cada fila en un objeto Document de LangChain."""
    print(f"Loading data from {nombre_archivo}...")
    
    try:
        df = pd.read_csv(nombre_archivo)
    except FileNotFoundError:
        print(f"❌ ERROR: Archivo CSV no encontrado en la ruta: {nombre_archivo}")
        return []

    documentos_coches = []
    
    for index, row in df.iterrows():
        # Contenido legible y optimizado para la búsqueda
        contenido = (
            f"Modelo: {row['Modelo']}. Precio: {row['Precio']}€. Año: {row['Año']}. "
            f"Kilometraje: {row['Km']} km. Combustible: {row['Combustible']}. "
            f"Link: {row['Link']}"
        )
        
        # Metadata
        documento = Document(
            page_content=contenido,
            metadata={
                "source": "Inventario Autofesa", 
                "Modelo": row['Modelo'],
                "Precio": row['Precio'],
                "Link": row['Link'],
                "Combustible": row['Combustible']
            }
        )
        documentos_coches.append(documento)
        
    print(f"✅ Creados {len(documentos_coches)} documentos para indexación.")
    return documentos_coches


# =========================================================================
# === FUNCIÓN AUXILIAR DE FILTRADO ESTRICTO (NUEVA TOOL DE PRECISIÓN) ===
# =========================================================================

def filtrar_coches_por_parametros(coches_raw: str, max_precio: Optional[int] = None, max_km: Optional[int] = None) -> str:
    """
    Aplica filtros estrictos (precio y kilometraje) sobre una lista de coches en formato RAW.
    Esta función mejora la precisión del RAG cuando los criterios son numéricos y exactos.
    """
    if "No se encontraron coches" in coches_raw or not coches_raw:
        return "No se encontraron coches que cumplan esos criterios en el inventario."

    coches_list = [item.strip() for item in coches_raw.split(';') if item.strip()]
    coches_filtrados = []

    # Regex que captura Precio y Kilometraje del formato: [Precio€] (...) (Combustible, Km, Año)
    # Grupo 1: (\d+)€ (Precio)
    # Grupo 2: (\d+) km (Km)
    regex = re.compile(r'\[(\d+)€\].*?\(.*?\s*(\d+)\s*km,\s*\d{4}\)')
    
    for coche_data in coches_list:
        match = regex.search(coche_data)
        
        if match:
            # Los grupos de la expresión regular: 1=Precio, 2=Km
            precio = int(match.group(1))
            km = int(match.group(2))
            
            pasa_filtro_precio = (max_precio is None) or (precio <= max_precio)
            pasa_filtro_km = (max_km is None) or (km <= max_km)
            
            if pasa_filtro_precio and pasa_filtro_km:
                coches_filtrados.append(coche_data)

    if not coches_filtrados:
        return "No se encontraron coches que cumplan esos criterios de filtrado estricto en el inventario."

    return "; ".join(coches_filtrados)


# =========================================================================
# === CONFIGURACIÓN DEL RETRIEVER Y CADENA RAG ===
# =========================================================================

# Ejecución de la lógica de carga (se ejecuta una vez al importar el módulo)
documentos = crear_documentos_desde_csv(NOMBRE_ARCHIVO_CSV)

# Inicialización de Embeddings y Vector Store
print(f"Indexing documents into ChromaDB at {CHROMA_DIR}...")
embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2") 

vectorstore = Chroma.from_documents(
    documents=documentos, 
    embedding=embeddings, 
    persist_directory=CHROMA_DIR,
    collection_name=COLLECTION_NAME
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 5}) 
print("✅ Base de conocimiento RAG lista. Retriever configurado.")

# --- PROMPT TEMPLATE ---
prompt_template_investigador = """
Eres el **Investigador de Mercado de Inventario**. Tu tarea es buscar en el inventario de coches de segunda mano
(proporcionado en el {context}) para encontrar modelos que coincidan con la PREGUNTA del usuario.

REGLAS OBLIGATORIAS:
1. SOLO usa la información proporcionada en el contexto. No inventes datos.
2. Si no encuentras coincidencias, responde: "No se encontraron coches que cumplan esos criterios en el inventario."
3. FORMATO DE SALIDA (CRUCIAL para el siguiente agente): Devuelve los coches encontrados como una LISTA SEPARADA POR PUNTO Y COMA (;) en una sola línea.
   Formato: Modelo [Precio€] (Combustible, Km, Año); Modelo [Precio€] (Combustible, Km, Año)

PREGUNTA del usuario: {question}

RESULTADOS ENCONTRADOS (USANDO EL FORMATO SOLICITADO):
"""

QA_PROMPT = PromptTemplate(
    template=prompt_template_investigador, 
    input_variables=["context", "question"] 
)

# --- CADENA RAG (RetrievalQA) ---
rag_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever, 
    chain_type_kwargs={"prompt": QA_PROMPT}
)


# =========================================================================
# === FUNCIÓN EXPORTABLE (LA TOOL FINAL DEL AGENTE INVESTIGADOR) ===
# =========================================================================

def investigar_inventario_coches(pregunta_de_busqueda: str, max_precio: Optional[int] = None, max_km: Optional[int] = None) -> str:
    """
    TOOL PRINCIPAL del Investigador de Mercado. Busca en la base de datos RAG 
    y opcionalmente aplica un filtro estricto por precio y kilometraje.

    Devuelve los resultados en un formato semi-estructurado (;) para el Analista.
    """
    print(f"\n🔍 Investigador ejecutando RAG para: '{pregunta_de_busqueda}'...")
    
    # 1. Búsqueda RAG (siempre se ejecuta)
    result = rag_chain.invoke({"query": pregunta_de_busqueda})
    coches_raw = result['result'].strip()
    
    # 2. Aplicar el filtro estricto si se proporcionan parámetros
    if max_precio is not None or max_km is not None:
        print(f"🔬 Aplicando filtro estricto: Max Precio={max_precio}€, Max Km={max_km}km...")
        
        # Llama a la nueva función auxiliar de filtrado
        coches_filtrados = filtrar_coches_por_parametros(coches_raw, max_precio=max_precio, max_km=max_km)
        return coches_filtrados
    
    # 3. Devuelve el resultado RAG sin filtrar si no hay parámetros
    return coches_raw


# =========================================================================
# === PRUEBA DE EJECUCIÓN DEL MÓDULO (OPCIONAL) ===
# =========================================================================

if __name__ == "__main__":
    print("\n--- Ejecutando prueba de módulo rag_agent.py ---")
    
    # Prueba RAG estándar
    pregunta_ejemplo_1 = "¿Qué coches de la marca BMW de color blanco tienes?"
    respuesta_1 = investigar_inventario_coches(pregunta_ejemplo_1)
    print(f"\n✅ Respuesta RAG estándar:\n{respuesta_1}")
    
    # Prueba RAG con filtro estricto
    pregunta_ejemplo_2 = "¿Qué coches diésel de la marca Mercedes tienen menos de 100000 km y cuestan menos de 25000 euros?"
    respuesta_2 = investigar_inventario_coches(pregunta_ejemplo_2, max_precio=25000, max_km=100000)
    print(f"\n✅ Respuesta RAG con filtro:\n{respuesta_2}")
    
    print("--------------------------------------------------")