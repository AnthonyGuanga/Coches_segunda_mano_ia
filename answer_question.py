import re
import json
from tools import get_weather_on_date, assess_testability, check_vehicle_safety
from tools import tools_dict, tools_description, format_tool_output
from rag_client import query as rag_query
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

if not os.getenv("GOOGLE_API_KEY"):
    raise ValueError("Necesitas GOOGLE_API_KEY")

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

provincias_coords = {
    "alava": (42.8514, -2.6720),
    "albacete": (38.9954, -1.8574),
    "alicante": (38.3452, -0.4810),
    "almeria": (37.1890, -2.3610),
    "asturias": (43.3619, -5.8494),
    "avila": (40.6565, -4.6810),
    "badajoz": (38.8794, -6.9703),
    "barcelona": (41.3851, 2.1734),
    "burgos": (42.3439, -3.6969),
    "caceres": (39.4767, -6.3728),
    "cadiz": (36.5213, -6.2767),
    "cantabria": (43.1828, -3.9873),
    "castellon": (39.9864, -0.0363),
    "ceuta": (35.8894, -5.3213),
    "ciudad_real": (38.9862, -3.9274),
    "cordoba": (37.8882, -4.7794),
    "cuenca": (40.0704, -2.1374),
    "girona": (41.9794, 2.8214),
    "granada": (37.1773, -3.5986),
    "guadalajara": (40.6333, -3.1667),
    "guipuzcoa": (43.3120, -1.9745),
    "huelva": (37.2614, -6.9447),
    "huesca": (42.1401, 0.4089),
    "illes balears": (39.6953, 3.0176),
    "jaen": (37.7796, -3.7849),
    "leon": (42.5987, -5.5671),
    "lleida": (41.6176, 0.6200),
    "lugo": (43.0125, -7.5550),
    "madrid": (40.4168, -3.7038),
    "malaga": (36.7213, -4.4214),
    "melilla": (35.2923, -2.9381),
    "murcia": (37.9922, -1.1307),
    "navarra": (42.6950, -1.6761),
    "ourense": (42.3407, -7.8631),
    "palencia": (42.0090, -4.5340),
    "pontevedra": (42.4300, -8.6440),
    "salamanca": (40.9701, -5.6635),
    "santa cruz de tenerife": (28.4682, -16.2546),
    "segovia": (40.9481, -4.1183),
    "sevilla": (37.3886, -5.9823),
    "soria": (41.7640, -2.4709),
    "tarragona": (41.1189, 1.2445),
    "teruel": (40.3440, -1.1065),
    "toledo": (39.8628, -4.0273),
    "valencia": (39.4699, -0.3763),
    "valladolid": (41.6523, -4.7245),
    "vizcaya": (43.2630, -2.9350),
    "zamora": (41.5034, -5.7445),
    "zaragoza": (41.6488, -0.8891)
}

def detect_province(user_text):
    """Detecta provincia mencionada en el texto del usuario."""
    text = user_text.lower()
    for prov in provincias_coords:
        if prov in text:
            return prov
    return None

def answer_question(user_question: str):
    uq = user_question.strip()
    if not uq:
        return "Escribe algo por favor."

    provincia_detected = detect_province(uq)
    latitude, longitude = (None, None)
    if provincia_detected:
        latitude, longitude = provincias_coords[provincia_detected]

    rag_result = rag_query(uq)
    context_answer = rag_result.get("answer") if rag_result.get("success") else None

    prompt = f"""
Eres un asistente experto en coches de segunda mano y en herramientas útiles.
Dispones de estas funciones:

{tools_description}

Indicaciones:
- Si la pregunta menciona coches y hay información en RAG, úsala como contexto.
- Para clima o testabilidad, si detectas provincia, completa latitud/longitud.
- Para seguridad de vehículos, detecta marca, modelo, año y VIN si existe.
- Devuelve siempre texto humano, no código.
- Si debes usar una herramienta, genera JSON:
  {{"action":"tool","tool_name":"...","parameters":{{...}}}}
- Si no necesitas herramienta, genera JSON:
  {{"action":"response","response":"Texto de respuesta"}}

Provincia detectada: {provincia_detected}
Pregunta: {uq}
Contexto RAG: {context_answer or "No hay información relevante"}
"""

    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        gemini_text = resp.text
    except Exception as e:
        return f"Error al procesar la pregunta: {e}"

    try:
        m = re.search(r"\{.*\}", gemini_text, re.DOTALL)
        parsed = json.loads(m.group()) if m else {}
    except Exception:
        parsed = {}

    if parsed.get("action") == "tool":
        name = parsed.get("tool_name")
        params = parsed.get("parameters", {})
        if name in ["get_weather_on_date", "assess_testability"] and latitude and longitude:
            params["latitude"] = latitude
            params["longitude"] = longitude
        func = tools_dict.get(name)
        if func:
            return format_tool_output(name, func(**params))
        return f"Función '{name}' no encontrada."
    elif parsed.get("action") == "response":
        return parsed.get("response", context_answer or "No puedo responder eso.")
    else:
        return context_answer or gemini_text
