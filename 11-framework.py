import os
import re
import gradio as gr
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import httpx
import xml.etree.ElementTree as ET


# ---- 1. IMPORTS LANGCHAIN (CUMPLIENDO REQUISITOS) ----
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import WebBaseLoader, CSVLoader  # ✅ REQUISITO: Data Loaders
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
    """ ✅ REQUISITO CUMPLIDO: Usar Data Loaders de LangChain para la base de conocimiento """
    if not os.path.exists(CSV_PATH):
        return [LangchainDocument(
            page_content="Modelo: BMW Serie 3. Precio: 20000. Link: http://auto.com/1",
            metadata={"Link": "http://auto.com/1", "Precio": "20000"}
        )]

    print("📚 Cargando CSV con LangChain CSVLoader...")
    loader = CSVLoader(file_path=CSV_PATH, encoding="utf-8")
    docs = loader.load()
    for doc in docs:
        if "Link" not in doc.metadata:
            doc.metadata["Link"] = "http://autofesa.com"
    return docs

print("⏳ Creando Base de Conocimiento RAG (FAISS)...")
lc_docs = cargar_datos_langchain()
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectorstore = FAISS.from_documents(lc_docs, embeddings)
print("✅ RAG Listo.")

# =========================
# 4. PROMPT TEMPLATES
# =========================
lc_prompt_vendedor = PromptTemplate(
    input_variables=["documents", "query"],
    template_format="jinja2",
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

lc_prompt_analista = PromptTemplate(
    input_variables=["external_data", "documents"],
    template_format="jinja2",
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

lc_prompt_gerente = PromptTemplate(
    input_variables=["draft_text"],
    template_format="jinja2",
    template="""
Rol: Gerente de Calidad y Experto en comunicación con clientes.
Borrador recibido:
{{ draft_text }}
Tarea: 
1. Reescribe el mensaje para que sea **claro, fluido y persuasivo**, listo para enviar al cliente.
2. Asegúrate de que todos los datos sean **exactos y coincidan con el inventario** (precio, link, modelo, año, etc.).
3. Elimina saludos genéricos, placeholders o frases redundantes.
4. Mantén un estilo profesional pero cercano, con párrafos cortos y fáciles de leer.
5. No agregues información que no esté en el borrador ni inventes detalles.
Salida: Solo el texto final pulido, listo para enviar, sin notas ni explicaciones adicionales.
"""
)

# =========================
# 5. COMPONENTES
# =========================
@component
class InventoryAgent:
    @component.output_types(documents=List[Document])
    def run(self, query: str):
        print(f"🐶 [Sabueso - RAG] Buscando: '{query[:40]}...'")
        results = vectorstore.similarity_search(query, k=4)
        haystack_docs = []
        for doc in results:
            haystack_docs.append(Document(content=doc.page_content, meta=doc.metadata))
        return {"documents": haystack_docs}

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

# -------------------------
# NUEVO COMPONENTE: VEHICLE SAFETY
# -------------------------
@component
class VehicleSafetyComponent:
    @component.output_types(safety_report=dict)
    def run(self, make: str, model: str, year: int, vin: Optional[str] = None):
        recalls, recalls_error, safety_ratings = [], None, {}
        try:
            base_url = 'https://api.nhtsa.gov/recalls/recallsByVehicle'
            params = {'make': make, 'model': model, 'modelYear': year}
            r = httpx.get(base_url, params=params, timeout=10.0)
            r.raise_for_status()
            recalls_data = r.json() if r.text else {}
            for rec in recalls_data.get('results', []):
                recalls.append({
                    'campaign_number': rec.get('NHTSACampaignNumber') or rec.get('CampaignNumber'),
                    'component': rec.get('Component'),
                    'summary': rec.get('Summary') or rec.get('RecallSummary'),
                    'date': rec.get('ReportReceivedDate') or rec.get('Date'),
                })
        except Exception as e_rec:
            recalls_error = str(e_rec)
            recalls = []

        try:
            safety_url = f'https://api.nhtsa.gov/SafetyRatings/vehicle/{year}/{make}/{model}'
            r = httpx.get(safety_url, timeout=10.0)
            r.raise_for_status()
            safety_json = r.json() if r.text else None
            if safety_json and isinstance(safety_json, dict):
                results = safety_json.get('results') or safety_json.get('Results')
                if results:
                    first = results[0]
                    safety_ratings = {
                        'overall_rating': first.get('OverallRating'),
                        'frontal_crash': first.get('FrontalCrashRating'),
                        'side_crash': first.get('SideCrashRating'),
                        'rollover': first.get('RolloverRating'),
                    }
        except Exception:
            safety_ratings = {}

        out = {
            'resolved': {'make': make, 'model': model, 'year': year},
            'total_recalls': len(recalls),
            'recalls': recalls,
            'safety_ratings': safety_ratings,
            'recommendations': []
        }
        if recalls:
            out['recommendations'].append('Verificar todos los recalls abiertos antes de comprar')
        if safety_ratings and safety_ratings.get('overall_rating'):
            out['recommendations'].append('Considerar calificaciones de seguridad en la decisión de compra')
        if recalls_error:
            out['error'] = recalls_error
        return {"safety_report": out}
    
    # -------------------------
# NUEVO COMPONENTE: VEHICLE FUEL ECONOMY
# -------------------------
@component
class VehicleFuelEconomyComponent:
    @component.output_types(fuel_report=dict)
    def run(self, make: str, model: str, year: int):
        vehicle_id = None
        fuel_data = {}
        error = None

        # 1. Buscar vehicleId en la API de la EPA
        try:
            search_url = "https://www.fueleconomy.gov/ws/rest/vehicle/menu/options"
            params = {"year": year, "make": make, "model": model}
            r = httpx.get(search_url, params=params, timeout=10.0)
            r.raise_for_status()

            root = ET.fromstring(r.text)
            option = root.find(".//menuItem")
            if option is not None:
                vehicle_id = option.find("value").text
        except Exception as e:
            error = f"No se pudo localizar el vehículo: {e}"

        # 2. Obtener datos de consumo
        if vehicle_id:
            try:
                detail_url = f"https://www.fueleconomy.gov/ws/rest/vehicle/{vehicle_id}"
                r = httpx.get(detail_url, timeout=10.0)
                r.raise_for_status()
                root = ET.fromstring(r.text)

                def get(tag):
                    el = root.find(tag)
                    return el.text if el is not None else None

                fuel_data = {
                    "fuel_type": get("fuelType"),
                    "city_mpg": get("city08"),
                    "highway_mpg": get("highway08"),
                    "combined_mpg": get("comb08"),
                    "co2_emissions": get("co2TailpipeGpm"),
                }
            except Exception as e:
                error = f"No se pudieron obtener datos de consumo: {e}"

        report = {
            "resolved": {"make": make, "model": model, "year": year},
            "fuel_data": fuel_data,
            "recommendations": [],
        }

        if fuel_data.get("combined_mpg"):
            report["recommendations"].append(
                "Buen candidato si buscas eficiencia en consumo."
            )

        if error:
            report["error"] = error

        return {"fuel_report": report}


# =========================
# 6. ORQUESTACIÓN (PIPELINES)
# =========================
print("⚙️ Configurando Pipelines...")

# --- PIPELINE VENTA ---
pipe_venta = Pipeline()
pipe_venta.add_component("sabueso", InventoryAgent())
pipe_venta.add_component("prompt_vendedor", PromptBuilder(template=lc_prompt_vendedor.template))
pipe_venta.add_component("llm_vendedor", GoogleAIGeminiGenerator(model="gemini-2.0-flash"))
pipe_venta.add_component("prompt_gerente", PromptBuilder(template=lc_prompt_gerente.template))
pipe_venta.add_component("llm_gerente", GoogleAIGeminiGenerator(model="gemini-2.0-flash"))
pipe_venta.connect("sabueso", "prompt_vendedor")
pipe_venta.connect("prompt_vendedor", "llm_vendedor")
pipe_venta.connect("llm_vendedor.replies", "prompt_gerente.draft_text")
pipe_venta.connect("prompt_gerente", "llm_gerente")

# --- PIPELINE COMPARADOR ---
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
# 7. INTERPRETE DE CONSULTAS DE SEGURIDAD
# =========================
def es_consulta_seguridad(texto: str) -> bool:
    return bool(re.search(r'\b(recalls?|seguridad|safety|aviso de seguridad|revisión)\b', texto, re.I))

def es_consulta_consumo(texto: str) -> bool:
    return bool(re.search(
        r'\b(consumo|combustible|gasolina|di[eé]sel|mpg|gasta)\b',
        texto,
        re.I
    ))


def mpg_a_litros_100km(mpg: float) -> float:
    """
    Convierte Millas por Galón (MPG - EE.UU.) a Litros por 100 km.
    Fórmula estándar:
    L/100km = 235.215 / MPG
    """
    try:
        mpg = float(mpg)
        if mpg <= 0:
            return None
        return round(235.215 / mpg, 1)
    except (TypeError, ValueError):
        return None

def formatear_informe_consumo(report: dict) -> str:
    resolved = report.get("resolved", {})
    data = report.get("fuel_data", {})
    recs = report.get("recommendations", [])

    make = resolved.get("make", "")
    model = resolved.get("model", "")
    year = resolved.get("year", "")

    final = ""
    final += "⛽ **INFORME OFICIAL DE CONSUMO Y EFICIENCIA**\n"
    final += f"Vehículo analizado: **{make} {model} ({year})**\n"
    final += "Fuente: Agencia de Protección Ambiental (EPA - EE.UU.)\n"
    final += "—" * 45 + "\n\n"

    if not data:
        final += "ℹ️ No se han encontrado datos oficiales de consumo para este vehículo."
        return final

    # Datos MPG
    city_mpg = data.get("city_mpg")
    highway_mpg = data.get("highway_mpg")
    combined_mpg = data.get("combined_mpg")

    # Conversión a L/100km
    city_l = mpg_a_litros_100km(city_mpg)
    highway_l = mpg_a_litros_100km(highway_mpg)
    combined_l = mpg_a_litros_100km(combined_mpg)

    final += "📊 **Consumo homologado**\n"

    if city_mpg and city_l:
        final += f"• Uso urbano: **{city_l} L/100 km** ({city_mpg} MPG)\n"
    else:
        final += "• Uso urbano: No disponible\n"

    if highway_mpg and highway_l:
        final += f"• Carretera: **{highway_l} L/100 km** ({highway_mpg} MPG)\n"
    else:
        final += "• Carretera: No disponible\n"

    if combined_mpg and combined_l:
        final += f"• Combinado: **{combined_l} L/100 km** ({combined_mpg} MPG)\n"
    else:
        final += "• Combinado: No disponible\n"

    final += "\n🌱 **Impacto medioambiental**\n"
    final += f"• Emisiones de CO₂: **{data.get('co2_emissions', '?')} g/milla**\n"
    final += f"• Tipo de combustible: **{data.get('fuel_type', 'No especificado')}**\n\n"

    if recs:
        final += "💡 **Evaluación experta**\n"
        final += f"{recs[0]}\n"

    final += "\nℹ️ *Nota: valores oficiales EPA (EE.UU.). El consumo real puede variar según conducción.*"

    return final

def interpretar_seguridad(texto: str) -> Dict[str, Any]:
    marcas = ["Ford","Toyota","BMW","Hyundai","Honda","Chevrolet","Nissan","Kia","Mercedes","Volkswagen"]
    make = None
    for m in marcas:
        if re.search(r'\b' + re.escape(m) + r'\b', texto, re.I):
            make = m
            break
    year_match = re.search(r'\b(19[8-9]\d|20[0-2]\d|2025)\b', texto)
    year = int(year_match.group(0)) if year_match else None
    model_match = None
    if make and year:
        pattern = re.compile(rf'{make}\s+([A-Za-z0-9\-]+)\s+{year}', re.I)
        m = pattern.search(texto)
        if m:
            model_match = m.group(1)
    model = model_match
    return {"make": make, "model": model, "year": year}

# =========================
# 8. LOGICA Y UI (MEJORADA Y FORMATEADA)
# =========================
def detectar_url(texto):
    match = re.search(r'(https?://\S+)', texto)
    return match.group(0) if match else None

def chat_logic(mensaje, history):
    url = detectar_url(mensaje)

    # --- CAMINO 1: SEGURIDAD (FORMATEADO BONITO) ---
    if es_consulta_seguridad(mensaje):
        print("🔄 WORKFLOW: SEGURIDAD/RECALLS")
        params = interpretar_seguridad(mensaje)
        
        if not all([params.get("make"), params.get("model"), params.get("year")]):
            final = "❌ No pude identificar el coche exacto. Por favor, prueba escribiendo: 'Recalls Ford Fusion 2014' o 'Seguridad BMW X5 2020'."
        else:
            # Llamamos a la Tool
            res = VehicleSafetyComponent().run(**params)
            report = res["safety_report"]
            
            # Encabezado del Informe
            final = f"🛡️ **INFORME DE SEGURIDAD OFICIAL (NHTSA)**\n"
            final += f"Vehículo: {report['resolved']['make']} {report['resolved']['model']} ({report['resolved']['year']})\n"
            final += "-" * 40 + "\n"

            # 1. Safety Ratings (Estrellas)
            ratings = report.get('safety_ratings', {})
            if ratings and ratings.get('overall_rating'):
                final += f"⭐ **Puntuación Global:** {ratings['overall_rating']}/5 Estrellas\n"
                final += f"   - Choque Frontal: {ratings.get('frontal_crash', '?')}/5\n"
                final += f"   - Choque Lateral: {ratings.get('side_crash', '?')}/5\n"
                final += f"   - Vuelco: {ratings.get('rollover', '?')}/5\n\n"
            else:
                final += "ℹ️ No hay datos de estrellas de choque disponibles.\n\n"

            # 2. Recalls (Llamadas a revisión)
            total = report['total_recalls']
            if total == 0:
                final += "✅ **ESTADO: EXCELENTE.**\nNo se han encontrado llamadas a revisión (recalls) para este vehículo."
            else:
                final += f"⚠️ **ESTADO: PRECAUCIÓN**\nSe han encontrado **{total} alertas de seguridad (Recalls)** reportadas al gobierno.\n\n"
                final += "**Últimos problemas reportados:**\n"
                
                # MOSTRAR SOLO LOS 3 PRIMEROS PARA NO SATURAR
                recalls = report['recalls']
                for i, rec in enumerate(recalls[:3]): 
                    fecha = rec['date']
                    pieza = rec['component']
                    # Cortamos el resumen si es muy largo
                    resumen = rec['summary'][:150] + "..." if len(rec['summary']) > 150 else rec['summary']
                    
                    final += f"🔴 **{fecha}** | Fallo en: {pieza}\n"
                    final += f"   _{resumen}_\n\n"
                
                if total > 3:
                    final += f"... y {total - 3} alertas más. (Consulta con el concesionario).\n"

            # 3. Recomendaciones
            if report['recommendations']:
                final += "-" * 40 + "\n💡 **Consejo del Experto:** " + report['recommendations'][0]
    
    elif es_consulta_consumo(mensaje):
        print("🔄 WORKFLOW: CONSUMO / EFICIENCIA")
        params = interpretar_seguridad(mensaje)

        if not all([params.get("make"), params.get("model"), params.get("year")]):
            final = "❌ No pude identificar el coche. Prueba: 'Consumo Toyota Corolla 2016'."
        else:
            res = VehicleFuelEconomyComponent().run(**params)
            final = formatear_informe_consumo(res["fuel_report"])

    # --- CAMINO 2: COMPARADOR WEB ---
    elif url:
        print(f"🔄 WORKFLOW: COMPARACIÓN")
        res = pipe_comparador.run(
            {"scraper": {"url": url}},
            include_outputs_from={"llm_analista"}
        )
        # final = res["llm_gerente"]["replies"][0] # A veces el gerente falla si no hay contexto, mejor ver al analista directo si quieres
        final = res["llm_gerente"]["replies"][0]

    # --- CAMINO 3: VENTA NORMAL ---
    else:
        print(f"🔄 WORKFLOW: VENTA")
        res = pipe_venta.run(
            {
                "sabueso": {"query": mensaje}, 
                "prompt_vendedor": {"query": mensaje}
            },
            include_outputs_from={"llm_vendedor"}
        )
        final = res["llm_gerente"]["replies"][0]

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
    msg = gr.Textbox(
        label="Mensaje",
        placeholder="Busco coche... o pega un link para comparar o consulta seguridad/consumo.",
    )
    msg.submit(chat_logic, [msg, chatbot], [msg, chatbot])

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", share=False)
