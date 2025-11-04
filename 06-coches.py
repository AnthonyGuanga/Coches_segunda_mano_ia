# app.py
import gradio as gr
from transformers import pipeline
from diffusers import StableDiffusionPipeline
import torch

# Detecta GPU automáticamente
device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.float16 if device == "cuda" else torch.float32

# 1️⃣ Generación de texto (GPT-2)
text_gen = pipeline("text-generation", model="gpt2", device=0 if device == "cuda" else -1)

# 2️⃣ Generación de imagen (Stable Diffusion)
model_id = "runwayml/stable-diffusion-v1-5"
image_gen = StableDiffusionPipeline.from_pretrained(model_id, torch_dtype=dtype)
image_gen.to(device)

# 🔧 Lógica principal
def generar_anuncio_y_imagen(descripcion):
    # Generar anuncio textual
    prompt_text = f"Crea un texto atractivo para vender este coche de segunda mano: {descripcion}"
    texto_generado = text_gen(prompt_text, max_length=120, temperature=0.8, top_p=0.9, do_sample=True)[0]["generated_text"]

    # Generar imagen del coche
    prompt_img = f"fotografía realista de un coche {descripcion}, aparcado en la calle, fondo neutro, luz natural"
    image = image_gen(prompt_img).images[0]

    return texto_generado, image

# 🎨 Interfaz con Gradio
demo = gr.Interface(
    fn=generar_anuncio_y_imagen,
    inputs=gr.Textbox(lines=2, placeholder="Ejemplo: Ford Focus 2017 gris diésel 100.000 km en buen estado"),
    outputs=[
        gr.Textbox(label="Anuncio generado"),
        gr.Image(label="Imagen del coche generado")
    ],
    title="🚗 Generador de anuncios de coches de segunda mano",
    description="Escribe una descripción y genera un anuncio completo con imagen realista usando IA de Hugging Face."
)

if __name__ == "__main__":
    demo.launch()
