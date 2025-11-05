# app.py
import gradio as gr
from transformers import pipeline
from diffusers import StableDiffusionPipeline, EulerDiscreteScheduler
import torch

# Detecta GPU automáticamente
device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.float16 if device == "cuda" else torch.float32

# 1️⃣ Generación de texto (Mistral-7B)
text_gen = pipeline("text-generation", model="mistralai/Mistral-7B-Instruct-v0.2", device=0 if device == "cuda" else -1)


# 2️⃣ Generación de imagen (Stable Diffusion v2-base)
model_id = "stabilityai/stable-diffusion-2-base"
scheduler = EulerDiscreteScheduler.from_pretrained(model_id, subfolder="scheduler")
image_gen = StableDiffusionPipeline.from_pretrained(
    model_id,
    scheduler=scheduler,
    torch_dtype=dtype
)
image_gen.to(device)

# 🔧 Lógica principal
def generar_anuncio_y_imagen(descripcion):
    # Generar anuncio textual (mejor prompt)
    prompt_text = (
        f"Escribe un anuncio breve y convincente para vender un coche de segunda mano. "
        f"Detalles: {descripcion}. "
        f"El texto debe sonar natural, confiable y atractivo:\n\n"
    )
    texto_generado = text_gen(prompt_text, max_length=120, temperature=0.8, top_p=0.9, do_sample=True)[0]["generated_text"]

    # Generar imagen del coche
    prompt_img = f"fotografía realista de un coche {descripcion}, aparcado en la calle, fondo neutro, luz natural"
    image = image_gen(prompt_img).images[0]

    return texto_generado, image


# 🎨 Interfaz con Gradio
demo = gr.Interface(
    fn=generar_anuncio_y_imagen,
    inputs=gr.Textbox(
        lines=2,
        placeholder="Ejemplo: Ford Focus 2017 gris diésel 100.000 km en buen estado",
        label="Descripción del coche"
    ),
    outputs=[
        gr.Textbox(label="Anuncio generado", lines=8, interactive=False),
        gr.Image(label="Imagen del coche generado")
    ],
    title="🚗 Generador de anuncios de coches de segunda mano",
    description="Escribe una descripción y genera un anuncio completo con imagen realista usando IA de Hugging Face."
)


if __name__ == "__main__":
    demo.launch()
