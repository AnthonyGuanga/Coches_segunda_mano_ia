import os
import statistics
import random
import gradio as gr
from typing import TypedDict, List
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

# --- 1. CONFIGURACIÓN DE CREDENCIALES ---

os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGCHAIN_ENDPOINT"] = ""
os.environ["LANGCHAIN_API_KEY"] = ""

# --- CONFIGURACIÓN DE API KEYS DESDE .env ---
from pathlib import Path
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

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
    car_model: str             
    search_results: List[str]  
    market_prices: List[float]
    analysis_text: str         
    is_sufficient: bool       
    final_file_path: str      
    pdf_file_path: str         
    audio_file_path: str      
    email_status: str          

# Herramienta 1: Búsqueda Web
search_tool = TavilySearch(max_results=3)


# Herramienta 2: Cálculo Matemático (Procesamiento)
@tool
def calculate_average_price(prices: List[float]) -> float:
    """Calcula la media aritmética de una lista de precios."""
    if not prices: return 0.0
    return statistics.mean(prices)

# Herramienta 3: Sistema de Archivos
@tool
def save_report_to_disk(content: str, filename: str) -> str:
    """Guarda el texto en un archivo .md y devuelve la ruta absoluta."""
    clean_name = "".join([c if c.isalnum() else "_" for c in filename]) + "_report.md"
    path = os.path.abspath(clean_name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path



from gtts import gTTS

@tool
def generate_audio_from_text(content: str, filename: str) -> str:
    """
    Convierte el texto en audio mp3 y devuelve la ruta del archivo.
    """
    clean_name = "".join([c if c.isalnum() else "_" for c in filename]) + "_report.mp3"
    path = os.path.abspath(clean_name)
    tts = gTTS(text=content, lang='es')
    tts.save(path)
    return path

from fpdf import FPDF

@tool
def generate_pdf_from_text(content: str, filename: str) -> str:
    """
    Convierte el texto en un archivo PDF y devuelve la ruta del archivo.
    """
    clean_name = "".join([c if c.isalnum() else "_" for c in filename]) + "_report.pdf"
    path = os.path.abspath(clean_name)
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_font('DejaVu', '', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', uni=True)
    pdf.set_font("DejaVu", size=12)

    for line in content.split("\n"):
        pdf.multi_cell(0, 6, line)
    
    pdf.output(path)
    return path

import smtplib
from email.message import EmailMessage
from langchain_core.tools import tool

@tool
def send_email_smtp_debug(
    recipient: str,
    subject: str,
    body: str
) -> str:
    """
    Envía un email usando SMTP real contra un servidor local de pruebas.
    No se envían correos reales a Internet.
    """
    msg = EmailMessage()
    msg["From"] = "ai-system@demo.com"
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP("localhost", 1025) as server:
            server.send_message(msg)

        return f"Email enviado vía SMTP simulado a {recipient}"

    except Exception as e:
        return f"Error en envío SMTP simulado: {str(e)}"


# --- 4. NODOS DEL GRAFO  ---

def researcher_node(state: AgentState):
    """AGENTE 1: Busca en la web y extrae datos."""
    print(f"🔎 [Investigador] Buscando datos para: {state['car_model']}...")
    try:
        results = search_tool.invoke(f"precio opiniones fallos {state['car_model']}")
        contents = [res['content'] for res in results]
    except Exception as e:
        contents = [f"Error buscando información: {e}"]

    # Simulación de extracción de precios 

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
    """AGENTE 3: Genera el entregable final y envia email."""
    print("🖨️ [Editor] Guardando archivo físico y enviando email...")
    
    final_content = f"# REPORTE AUTO-GENERADO\nFecha: 09-Enero\n\n{state['analysis_text']}"
    file_path_md = save_report_to_disk.invoke({"content": final_content, "filename": state['car_model']})
    file_path_mp3 = generate_audio_from_text.invoke({"content": final_content, "filename": state['car_model']})
    file_path_pdf = generate_pdf_from_text.invoke({"content": final_content, "filename": state['car_model']})
    email_result = send_email_smtp_debug.invoke({
    "recipient": "cliente@ejemplo.com",
    "subject": f"Informe automático sobre {state['car_model']}",
    "body": state['analysis_text'][:1000]
})

    
    return {
        "final_file_path": file_path_md,
        "audio_file_path": file_path_mp3,
        "pdf_file_path": file_path_pdf,
        "email_status": email_result
    }

# --- 5. CONSTRUCCIÓN DEL GRAFO  ---

def quality_gate(state: AgentState):
    return "approved" if state["is_sufficient"] else "rejected"

workflow = StateGraph(AgentState)

workflow.add_node("investigador", researcher_node)
workflow.add_node("analista", analyst_node)
workflow.add_node("editor", publisher_node)

workflow.set_entry_point("investigador")
workflow.add_edge("investigador", "analista")

workflow.add_conditional_edges(
    "analista",
    quality_gate,
    {
        "approved": "editor",
        "rejected": "investigador" 
    }
)
workflow.add_edge("editor", END)

app = workflow.compile()

# --- 6. INTERFAZ DE USUARIO (Gradio) ---

def run_multi_agent_system(car_input):
    """Función puente entre Gradio y LangGraph."""
    initial_state = {
        "car_model": car_input,
        "search_results": [],
        "market_prices": [],
        "analysis_text": "",
        "is_sufficient": False,
        "final_file_path": "",
        "pdf_file_path": "",     
        "audio_file_path": "",   
        "email_status": "" 
    }

    result = app.invoke(initial_state)
    return result["analysis_text"], result["final_file_path"], result["pdf_file_path"], result["audio_file_path"], result["email_status"]

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🏎️ Taller de Inteligencia Artificial: Análisis de Coches")
    gr.Markdown("Sistema Multi-Agente con LangGraph, Gemini y Tavily.")
    
    with gr.Row():
        with gr.Column():
            inp = gr.Textbox(label="Modelo de Coche", placeholder="Ej: Audi A3 2019")
            btn = gr.Button("Analizar", variant="primary")
        with gr.Column():
            out_txt = gr.Markdown(label="Resumen")
            out_file_md = gr.File(label="Descargar Informe MD")
            out_file_pdf = gr.File(label="Descargar Informe PDF")
            out_file_mp3 = gr.File(label="Descargar Audio MP3")
            out_email = gr.Textbox(label="Estado del Email")
            
    btn.click(
        run_multi_agent_system, 
        inputs=inp, 
        outputs=[out_txt, out_file_md, out_file_pdf, out_file_mp3, out_email]
    )

if __name__ == "__main__":
    demo.launch()
    