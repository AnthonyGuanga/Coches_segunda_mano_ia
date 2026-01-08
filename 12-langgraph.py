import os
import statistics
import random
import gradio as gr
from typing import TypedDict, List
from dotenv import load_dotenv
# Librerías de LangChain y LangGraph
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

# --- 1. CONFIGURACIÓN DE CREDENCIALES (Tu Lógica) ---
# --- DESACTIVAR LANGSMITH ---
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGCHAIN_ENDPOINT"] = ""
os.environ["LANGCHAIN_API_KEY"] = ""

# --- CONFIGURACIÓN DE API KEYS DESDE .env ---
load_dotenv()

GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")
TAVILY_KEY = os.getenv("TAVILY_API_KEY")

if not GOOGLE_KEY:
    raise RuntimeError("❌ GOOGLE_API_KEY no encontrada en el archivo .env")

if not TAVILY_KEY:
    raise RuntimeError("❌ TAVILY_API_KEY no encontrada en el archivo .env")

print("✅ API Keys cargadas desde .env\n")


# --- 2. CONFIGURACIÓN DEL MODELO ---
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0
)


# --- 3. DEFINICIÓN DEL ESTADO Y HERRAMIENTAS ---

class AgentState(TypedDict):
    car_model: str             # Input
    search_results: List[str]  # Datos recopilados
    market_prices: List[float] # Precios numéricos
    analysis_text: str         # Borrador del informe
    is_sufficient: bool        # Control de calidad
    final_file_path: str       # Ruta del archivo final

# Herramienta 1: Búsqueda Web
search_tool = TavilySearch(max_results=3)


# Herramienta 2: Cálculo Matemático (Procesamiento)
@tool
def calculate_average_price(prices: List[float]) -> float:
    """Calcula la media aritmética de una lista de precios."""
    if not prices: return 0.0
    return statistics.mean(prices)

# Herramienta 3: Sistema de Archivos (Salida Real)
@tool
def save_report_to_disk(content: str, filename: str) -> str:
    """Guarda el texto en un archivo .md y devuelve la ruta absoluta."""
    clean_name = "".join([c if c.isalnum() else "_" for c in filename]) + "_report.md"
    path = os.path.abspath(clean_name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path

# --- 4. NODOS DEL GRAFO (AGENTES) ---

def researcher_node(state: AgentState):
    """AGENTE 1: Busca en la web y extrae datos."""
    print(f"🔎 [Investigador] Buscando datos para: {state['car_model']}...")
    try:
        results = search_tool.invoke(f"precio opiniones fallos {state['car_model']}")
        contents = [res['content'] for res in results]
    except Exception as e:
        contents = [f"Error buscando información: {e}"]

    # Simulación de extracción de precios (mock)
    # En producción usaríamos un parser LLM para sacar los números del texto
    base_price = 20000 if "seat" in state['car_model'].lower() else 40000
    mock_prices = [base_price + random.randint(-3000, 3000) for _ in range(3)]
    
    return {"search_results": contents, "market_prices": mock_prices}

def analyst_node(state: AgentState):
    """AGENTE 2: Procesa los datos y escribe."""
    print("🧠 [Analista] Redactando informe...")

    avg_price = calculate_average_price.invoke(
        {"prices": state["market_prices"]}
    )

    context_str = "\n".join(state['search_results'])

    prompt = f"""
    Eres un consultor de automoción experto.

    COCHE: {state['car_model']}
    DATOS WEB: {context_str}
    PRECIO MEDIO CALCULADO: {avg_price} €

    Escribe un informe en Markdown que incluya:
    1. Título y Resumen.
    2. Análisis de precios (¿Es {avg_price}€ un buen precio?).
    3. Lista de puntos clave (Pros/Contras).
    """

    response = llm.invoke([HumanMessage(content=prompt)])

    valid = len(response.content) > 100
    return {
        "analysis_text": response.content,
        "is_sufficient": valid
    }


def publisher_node(state: AgentState):
    """AGENTE 3: Genera el entregable final."""
    print("🖨️ [Editor] Guardando archivo físico...")
    
    final_content = f"# REPORTE AUTO-GENERADO\nFecha: 09-Enero\n\n{state['analysis_text']}"
    
    # Usa herramienta de disco
    file_path = save_report_to_disk.invoke({"content": final_content, "filename": state['car_model']})
    return {"final_file_path": file_path}

# --- 5. CONSTRUCCIÓN DEL GRAFO (LangGraph) ---

def quality_gate(state: AgentState):
    return "approved" if state["is_sufficient"] else "rejected"

workflow = StateGraph(AgentState)

# Añadir nodos
workflow.add_node("investigador", researcher_node)
workflow.add_node("analista", analyst_node)
workflow.add_node("editor", publisher_node)

# Definir flujo
workflow.set_entry_point("investigador")
workflow.add_edge("investigador", "analista")

# Lógica condicional (Router)
workflow.add_conditional_edges(
    "analista",
    quality_gate,
    {
        "approved": "editor",
        "rejected": "investigador" # Reintentar si el informe es malo
    }
)
workflow.add_edge("editor", END)

app = workflow.compile()

# --- 6. INTERFAZ DE USUARIO (Gradio) ---

def run_multi_agent_system(car_input):
    """Función puente entre Gradio y LangGraph."""
    initial_state = {
        "car_model": car_input,
        "search_results": [], "market_prices": [],
        "analysis_text": "", "is_sufficient": False, "final_file_path": ""
    }
    
    # Invocar el grafo
    result = app.invoke(initial_state)
    return result["analysis_text"], result["final_file_path"]

# Diseño visual
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🏎️ Taller de Inteligencia Artificial: Análisis de Coches")
    gr.Markdown("Sistema Multi-Agente con LangGraph, Gemini y Tavily.")
    
    with gr.Row():
        with gr.Column():
            inp = gr.Textbox(label="Modelo de Coche", placeholder="Ej: Audi A3 2019")
            btn = gr.Button("Analizar", variant="primary")
        with gr.Column():
            out_txt = gr.Markdown(label="Resumen")
            out_file = gr.File(label="Descargar Informe")
            
    btn.click(run_multi_agent_system, inputs=inp, outputs=[out_txt, out_file])

if __name__ == "__main__":
    demo.launch()