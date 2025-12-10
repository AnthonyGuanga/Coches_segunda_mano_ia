#!/usr/bin/env python3
# main.py - Reemplazo Autogen -> Microsoft Agent Framework (con fallback)
import os
import sys
from pathlib import Path
import json
import re
import requests
import pandas as pd
import nest_asyncio
from typing import Annotated, Optional, Dict, Any
from dotenv import load_dotenv

# Vector store / embeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

# UI
import gradio as gr

# Parche para event loop con Gradio si fuera necesario
nest_asyncio.apply()

# Cargar .env
load_dotenv()

# ---- Config ----
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
CSV_PATH = DATA_DIR / "autofesa_completo_20251202_0932.csv"

# Keys / LLM config
# Si usas Gemini via Google Cloud o OpenAI-compatible endpoint fíjalos aquí
GEMINI_API_URL = os.getenv("GEMINI_API_URL", "").strip()  # e.g. https://api.openai.com/v1/chat/completions
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", "")).strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY", GEMINI_API_KEY)

if not GOOGLE_KEY:
    print("⚠️ AVISO: No se encontró GOOGLE_API_KEY/GEMINI_API_KEY en .env. Si quieres usar LLMs, añade la clave.")
    # no hacemos sys.exit para permitir modo sin LLM

# ---- Cargar datos / crear RAG ----
def cargar_datos():
    if not CSV_PATH.exists():
        print(f"⚠️ Archivo {CSV_PATH.name} no encontrado. Generando datos de prueba...")
        datos_prueba = [
            {"Modelo": "BMW Serie 3", "Precio": 20000, "Km": 50000, "Combustible": "Diesel", "Año": 2019, "Link": "http://auto.com/1"},
            {"Modelo": "Audi A4", "Precio": 15000, "Km": 80000, "Combustible": "Diesel", "Año": 2018, "Link": "http://auto.com/2"},
            {"Modelo": "Ford Fiesta", "Precio": 8000, "Km": 30000, "Combustible": "Gasolina", "Año": 2020, "Link": "http://auto.com/3"},
            {"Modelo": "Toyota Corolla", "Precio": 18500, "Km": 15000, "Combustible": "Híbrido", "Año": 2021, "Link": "http://auto.com/4"}
        ]
        df = pd.DataFrame(datos_prueba)
        df.to_csv(CSV_PATH, index=False)
        print(f"✅ Archivo de prueba creado en: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH)
    df['Precio'] = pd.to_numeric(df['Precio'], errors='coerce').fillna(0).astype(int)
    df['Km'] = pd.to_numeric(df['Km'], errors='coerce').fillna(0).astype(int)

    docs = []
    for _, row in df.iterrows():
        contenido = f"Coche: {row['Modelo']}. {row['Combustible']}. Año {row['Año']}."
        meta = {"Modelo": row['Modelo'], "Precio": int(row['Precio']), "Km": int(row['Km']), "Link": row.get('Link', '')}
        docs.append(Document(page_content=contenido, metadata=meta))
    return docs

print("⏳ Generando Embeddings y Base de Datos Vectorial...")
docs = cargar_datos()
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectorstore = FAISS.from_documents(docs, embeddings)
print("✅ Sistema RAG listo.")

# ---- La herramienta (igual que tenías) ----
def tool_buscar_inventario(
    consulta: Annotated[str, "Descripción del coche que busca el usuario (ej: 'BMW deportivo')"],
    precio_max: Annotated[Optional[int], "Presupuesto máximo en euros. Usa None si no se especifica."] = None,
    km_max: Annotated[Optional[int], "Kilometraje máximo. Usa None si no se especifica."] = None
) -> str:
    print(f"\n🔍 HERRAMIENTA INVOCADA: '{consulta}' | Max €: {precio_max} | Max Km: {km_max}")
    results = vectorstore.similarity_search(consulta, k=15)
    if not results:
        return "No se encontraron resultados semánticos."
    filtrados = []
    for doc in results:
        meta = doc.metadata
        precio_coche = meta.get("Precio", 9999999)
        km_coche = meta.get("Km", 9999999)
        cumple_precio = (precio_max is None) or (precio_coche <= precio_max)
        cumple_km = (km_max is None) or (km_coche <= km_max)
        if cumple_precio and cumple_km:
            info = f"- {meta['Modelo']} | {precio_coche}€ | {km_coche}km | [Ver]({meta.get('Link','')})"
            filtrados.append(info)
    if not filtrados:
        return f"Encontré coches tipo '{consulta}', pero ninguno cumple los filtros de precio (<{precio_max}) o km (<{km_max})."
    return "Coches encontrados:\n" + "\n".join(filtrados[:5])

# ---- Intento de integrar Microsoft Agent Framework (MAF) para Python ----
maf_available = False
maf_agent_obj = None
maf_runtime = None

try:
    # Intentamos importar el cliente según la doc (puede variar por versión)
    # Documentación muestra `from agent_framework.azure import AzureOpenAIChatClient`
    from agent_framework.azure import AzureOpenAIChatClient
    from azure.identity import AzureCliCredential, DefaultAzureCredential
    maf_available = True
    print("✅ agent-framework importado: intentando crear cliente AzureOpenAIChatClient (MAF).")
except Exception as e:
    # Intento alternativo: importar API genérica
    try:
        import agent_framework as af
        maf_available = True
        print("✅ agent-framework paquete encontrado. Procederemos con API genérica.")
    except Exception:
        maf_available = False
        print("⚠️ agent-framework no está disponible o no se pudo importar. Se usará fallback local.")

if maf_available:
    try:
        # 1) Si dispones de Azure credentials CLI, usamos AzureCliCredential
        try:
            credential = AzureCliCredential()
        except Exception:
            credential = DefaultAzureCredential()

        # 2) Crear cliente (según doc)
        try:
            client = AzureOpenAIChatClient(credential=credential)
            # Crear agente simple con instrucciones
            maf_agent_obj = client.create_agent(
                instructions=(
                    "Eres un vendedor experto de Autofesa. "
                    "Siempre que se te pida buscar coches, llama a la herramienta 'buscar_inventario' "
                    "con los parámetros (consulta, precio_max, km_max). Resume 3-5 mejores coches."
                ),
                name="vendedor"
            )
            print("✅ Agente MAF creado vía AzureOpenAIChatClient.")
        except Exception as e_inner:
            # Fallback: usar API genérica del paquete
            try:
                # varias implementaciones prueban con agent_framework.Agent etc.
                if hasattr(af, "Agent"):
                    maf_agent_obj = af.Agent(
                        name="vendedor",
                        instructions=(
                            "Eres un vendedor experto de Autofesa. "
                            "Siempre que se te pida buscar coches, llama a la herramienta 'buscar_inventario' "
                            "con los parámetros (consulta, precio_max, km_max). Resume 3-5 mejores coches."
                        ),
                        model={"model": GEMINI_MODEL, "api_key": GEMINI_API_KEY}
                    )
                    print("✅ Agente MAF creado con af.Agent (fallback genérico).")
                else:
                    print("⚠️ agent_framework instalado pero no encuentro API conocida; usaré fallback.")
                    maf_available = False
            except Exception:
                print("⚠️ No se pudo crear agente MAF con el paquete instalado. Usaremos fallback.")
                maf_available = False

    except Exception as exc:
        print("⚠️ Error inicializando MAF:", exc)
        maf_available = False

# Intentar registrar la tool si MAF está disponible y la API lo permite
if maf_available and maf_agent_obj is not None:
    try:
        # Intento de registro típico (la API real puede variar)
        # Doc ejemplo (puede cambiar): maf_agent_obj.register_tool(name="buscar_inventario", func=tool_buscar_inventario)
        if hasattr(maf_agent_obj, "register_tool"):
            maf_agent_obj.register_tool(name="buscar_inventario", func=tool_buscar_inventario, description="Busca coches")
            print("✅ Tool 'buscar_inventario' registrada en MAF (register_tool).")
        elif hasattr(maf_agent_obj, "add_tool"):
            maf_agent_obj.add_tool("buscar_inventario", tool_buscar_inventario)
            print("✅ Tool 'buscar_inventario' registrada en MAF (add_tool).")
        else:
            print("⚠️ El objeto agente MAF no tiene método conocido para registrar tools (register_tool/add_tool).")
            print("     Deberás registrar la función manualmente según la versión de agent-framework instalada.")
    except Exception as e:
        print("⚠️ Falló el registro automático de la tool en MAF:", e)
        print("⚠️ Continuaremos, pero es posible que debas registrar la tool manualmente según la API del paquete.")

# ---- Utilidades: extraer JSON de texto (para orquestación) ----
def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    match = re.search(r'(\{(?:[^{}]|(?R))*\})', text, flags=re.DOTALL)
    if not match:
        try:
            return json.loads(text)
        except Exception:
            return None
    snippet = match.group(1)
    try:
        return json.loads(snippet)
    except Exception:
        try:
            return json.loads(snippet.replace("'", '"'))
        except Exception:
            return None

# ---- Fallback orchestrator (si MAF no está disponible o no logra registrar tool) ----
def orchestrator_fallback(user_message: str) -> str:
    """
    Orquestador simple que usa el LLM (Gemini/OpenAI) para decidir si ejecutar la tool.
    Si no hay LLM configurado, realiza heurística local.
    """
    # Si no LLM configurado → heurística
    if not GEMINI_API_URL or not GEMINI_API_KEY:
        # heurística simple
        if any(w in user_message.lower() for w in ["precio", "euros", "€", "menos de", "hasta"]):
            nums = re.findall(r'\d+', user_message.replace('.', ''))
            precio = int(nums[0]) if nums else None
            consulta = user_message
            return tool_buscar_inventario(consulta, precio, None)
        return "Modo local: configura GEMINI_API_URL y GEMINI_API_KEY para orquestación avanzada."

    # Construir prompt para pedir JSON estricto
    system_instructions = (
        "Eres un orquestador. Analiza la petición y responde solo un JSON válido.\n"
        "Si debes llamar a la herramienta buscar_inventario, responde:\n"
        '{"call_tool": true, "consulta": "<texto>", "precio_max": <num|null>, "km_max": <num|null>}\n'
        "Si NO debes llamar, responde:\n"
        '{"call_tool": false, "text": "<respuesta>"}\n'
        "RESPONDE ÚNICAMENTE JSON."
    )
    prompt = system_instructions + "\nUsuario: " + user_message

    headers = {"Authorization": f"Bearer {GEMINI_API_KEY}", "Content-Type": "application/json"}
    # Soporte para OpenAI-compatible chat completions
    if "openai" in GEMINI_API_URL or "/v1/chat" in GEMINI_API_URL:
        payload = {
            "model": GEMINI_MODEL,
            "messages": [{"role": "system", "content": system_instructions}, {"role": "user", "content": user_message}],
            "temperature": 0
        }
        resp = requests.post(GEMINI_API_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except Exception:
            content = resp.text
    else:
        payload = {"model": GEMINI_MODEL, "prompt": prompt, "temperature": 0}
        resp = requests.post(GEMINI_API_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        try:
            data = resp.json()
            content = data.get("output") or resp.text
        except Exception:
            content = resp.text

    parsed = extract_json_from_text(content)
    if not parsed:
        return f"[LLM NO RESPONDIÓ JSON]\n{content}"

    if parsed.get("call_tool", False):
        consulta = parsed.get("consulta") or user_message
        precio_max = parsed.get("precio_max")
        km_max = parsed.get("km_max")
        tool_result = tool_buscar_inventario(consulta, precio_max, km_max)

        # Pedimos al LLM sintetizar como vendedor
        synth_prompt = (
            "Eres un vendedor profesional. Usuario: " + user_message + "\n"
            "Estos son los resultados de la búsqueda:\n" + tool_result + "\n\n"
            "Resume los 3-5 mejores coches en tono vendedor, breve."
        )
        if "openai" in GEMINI_API_URL or "/v1/chat" in GEMINI_API_URL:
            payload2 = {"model": GEMINI_MODEL, "messages": [{"role": "user", "content": synth_prompt}], "temperature": 0}
            resp2 = requests.post(GEMINI_API_URL, headers=headers, json=payload2, timeout=30)
            resp2.raise_for_status()
            data2 = resp2.json()
            try:
                synth_text = data2["choices"][0]["message"]["content"]
            except Exception:
                synth_text = resp2.text
        else:
            payload2 = {"model": GEMINI_MODEL, "prompt": synth_prompt, "temperature": 0}
            resp2 = requests.post(GEMINI_API_URL, headers=headers, json=payload2, timeout=30)
            resp2.raise_for_status()
            try:
                data2 = resp2.json()
                synth_text = data2.get("output") or resp2.text
            except Exception:
                synth_text = resp2.text
        return synth_text.strip()
    else:
        return parsed.get("text", "[LLM respondió sin campo 'text']")

# ---- chat_logic: usa MAF si está disponible, sino fallback ----
def chat_logic(mensaje, history):
    if history is None:
        history = []
    print(f"👤 Usuario: {mensaje}")

    respuesta = ""
    # Si MAF está disponible y tenemos un agente objeto con método run -> intenta usarlo
    if maf_available and maf_agent_obj is not None:
        try:
            # Intenta ejecutar de la forma simple mostrada en la doc: await agent.run(...)
            # Aquí hacemos síncrono para Gradio con run blocking
            # Muchas implementaciones exponen run or run_async; probamos ambos
            if hasattr(maf_agent_obj, "run"):
                # si run es coroutine, usar asyncio
                import asyncio
                if asyncio.iscoroutinefunction(maf_agent_obj.run):
                    respuesta_obj = asyncio.run(maf_agent_obj.run(mensaje))
                else:
                    respuesta_obj = maf_agent_obj.run(mensaje)
                # intentar extraer texto según estructura
                if isinstance(respuesta_obj, dict):
                    respuesta = respuesta_obj.get("text") or respuesta_obj.get("output") or str(respuesta_obj)
                else:
                    respuesta = getattr(respuesta_obj, "text", None) or str(respuesta_obj)
                # Si la respuesta parece pedir llamada a la tool y la tool no fue realmente llamada,
                # dependerá de si MAF internamente llama a la tool registrada.
            else:
                raise RuntimeError("El objeto agente MAF no tiene método 'run'.")
        except Exception as e:
            print("⚠️ Error ejecutando agente MAF:", e)
            print("⚠️ Se usará el orquestador fallback.")
            try:
                respuesta = orchestrator_fallback(mensaje)
            except Exception as ex2:
                respuesta = f"Error fallback orchestrator: {ex2}"
    else:
        # fallback
        try:
            respuesta = orchestrator_fallback(mensaje)
        except Exception as e:
            respuesta = f"Error en orquestador fallback: {e}"

    history.append({"role": "user", "content": mensaje})
    history.append({"role": "assistant", "content": respuesta})

    return "", history

# ---- Gradio UI ----
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🤖 Autofesa AI Assistant (MAF / Fallback)")
    chatbot = gr.Chatbot(type="messages", height=450)
    msg = gr.Textbox(label="Escribe tu consulta...", placeholder="Busco un coche por menos de 15000 euros...")
    clear = gr.Button("Limpiar Chat")
    msg.submit(chat_logic, [msg, chatbot], [msg, chatbot])
    clear.click(lambda: None, None, chatbot, queue=False)

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False)
