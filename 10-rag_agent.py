import os
import pandas as pd
from datetime import datetime
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_core.documents import Document 
from langchain_classic.chains.retrieval_qa.base import RetrievalQA # Tu importación corregida
from langchain_core.prompts import PromptTemplate 
from langchain_google_genai import ChatGoogleGenerativeAI

# 🚨 ADVERTENCIA DE SEGURIDAD: 
# Debes reemplazar 'AIzaSyA6JVn8W47K6kuqvb1QqxZ512x15s50AOo' con os.getenv('GOOGLE_API_KEY') 
# en un entorno de producción, pero lo dejamos como variable global para la prueba rápida.

# --- CONFIGURACIÓN GLOBAL ---
LLM_API_KEY_MANUAL = "AIzaSyA6JVn8W47K6kuqvb1QqxZ512x15s50AOo" 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NOMBRE_ARCHIVO_CSV = os.path.join(BASE_DIR, "autofesa_completo_20251127_1029.csv")
# 3. Definir la ruta para ChromaDB (también usando os.path.join)
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db") 
# -------------------------------------------------------------
COLLECTION_NAME = "inventario_coches_autofesa"

# =========================================================================
# === BLOQUE 1: CARGAR Y TRANSFORMAR DATOS ===
# =========================================================================

def crear_documentos_desde_csv(nombre_archivo: str) -> list[Document]:
    """Carga el CSV y convierte cada fila en un objeto Document de LangChain."""
    print(f"Loading data from {nombre_archivo}...")
    
    # Intenta leer el archivo
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
        
        # Metadata para referencias
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
# === BLOQUE 2 & 3: CONFIGURACIÓN RAG Y TOOL ===
# =========================================================================

# --- 1. CONFIGURACIÓN DEL LLM ---
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash", 
    temperature=0,
    google_api_key=LLM_API_KEY_MANUAL 
)

# --- 2. CONFIGURACIÓN DEL RETRIEVER ---
# Ejecución de la lógica de carga (se ejecuta una vez al importar el módulo)
documentos = crear_documentos_desde_csv(NOMBRE_ARCHIVO_CSV)

# Inicialización de Embeddings y Vector Store
print(f"Indexing documents into ChromaDB at {CHROMA_DIR}...")
embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2") 

# El VectorStore se crea o se carga desde disco si ya existe
vectorstore = Chroma.from_documents(
    documents=documentos, 
    embedding=embeddings, 
    persist_directory=CHROMA_DIR,
    collection_name=COLLECTION_NAME
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 5}) 
print("✅ Base de conocimiento RAG lista. Retriever configurado.")

# --- 3. PROMPT TEMPLATE ---
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

# --- 4. CADENA RAG (RetrievalQA) ---
rag_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever, 
    chain_type_kwargs={"prompt": QA_PROMPT}
)

# --- 5. FUNCIÓN EXPORTABLE (LA TOOL) ---

def investigar_inventario_coches(pregunta_de_busqueda: str) -> str:
    """
    TOOL PRINCIPAL del Investigador de Mercado. Busca en la base de datos RAG 
    para encontrar coches que coincidan con los criterios de búsqueda. 
    Devuelve los resultados en un formato semi-estructurado para el Analista.
    """
    print(f"\n🔍 Investigador ejecutando RAG para: '{pregunta_de_busqueda}'...")
    
    # Invoca la cadena RAG que contiene el LLM, el prompt y el retriever
    result = rag_chain.invoke({"query": pregunta_de_busqueda})
    
    return result['result'].strip()

# =========================================================================
# === PRUEBA DE EJECUCIÓN DEL MÓDULO (OPCIONAL) ===
# =========================================================================

if __name__ == "__main__":
    print("\n--- Ejecutando prueba de módulo rag_agent.py ---")
    pregunta_ejemplo = "¿Qué coches de la marca Alfa Romeo tienes, dame al menos 2, indicando su precio y kilometraje?"
    respuesta = investigar_inventario_coches(pregunta_ejemplo)
    print(f"\n✅ Respuesta del Agente RAG:\n{respuesta}")
    print("--------------------------------------------------")