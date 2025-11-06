# =====================================================
# 🚗 Generador de Flyers Automáticos (todo con IA visual)
# =====================================================


#Flyer publicitario de un coche Audi A3 2020 gris metálico, 50.000 km, en excelente estado. 
#Incluye texto en español con una oferta llamativa y un eslogan corto. 
#Diseño moderno, fondo urbano y tipografía elegante.

import torch
import gradio as gr
from diffusers import AutoPipelineForText2Image

# --- Configuración del dispositivo ---
device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.float16 if device == "cuda" else torch.float32
print(f"✅ Usando dispositivo: {device}")

# --- Cargar modelo de imagen rápido ---
print("Cargando modelo sd-turbo...")
image_gen = AutoPipelineForText2Image.from_pretrained(
    "stabilityai/sd-turbo",
    torch_dtype=dtype
).to(device)
print("✅ Modelo cargado correctamente.")

# --- Función principal ---
def generar_flyer_auto(descripcion):
    prompt = (
        f"Flyer publicitario de alta calidad para vender un coche {descripcion}. "
        f"Debe verse moderno y realista, con texto en español que incluya el nombre del coche, "
        f"una oferta atractiva y un eslogan corto. Fondo limpio y profesional, estilo publicitario."
    )

    image = image_gen(
        prompt,
        num_inference_steps=4,
        guidance_scale=0.5
    ).images[0]

    return image

# --- Interfaz en Gradio ---
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("## 🚗 Generador de Flyers de Coches (IA Visual Única)")

    inp = gr.Textbox(
        label="Descripción del coche",
        placeholder="Ejemplo: Mercedes-Benz Clase A gris 2021, 30.000 km, excelente estado"
    )
    btn = gr.Button("Generar Flyer", variant="primary")
    out = gr.Image(label="Flyer generado")

    btn.click(generar_flyer_auto, inp, out)

demo.launch(share=True)
