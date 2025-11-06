# ============================================
# 🚗 Generador de anuncios de coches en español (Colab ready)
# ============================================


import torch
import gradio as gr
from transformers import pipeline
from diffusers import StableDiffusionPipeline, EulerDiscreteScheduler

# --- Configuración del dispositivo ---
device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.float16 if device == "cuda" else torch.float32
device_id = 0 if device == "cuda" else -1
print(f"✅ Usando dispositivo: {device}")

# --- Modelo de texto (T5 español oficial del PlanTL) ---
print("Cargando modelo de texto (PlanTL-GOB-ES/t5-base-spanish)...")
# Intentamos cargar el modelo preferido; si falla (404 / privado), caemos a un modelo público pequeño.
try:
    text_gen = pipeline(
        "text2text-generation",
        model="PlanTL-GOB-ES/t5-base-spanish",
        device=device_id
    )
    print("✅ Modelo de texto cargado correctamente: PlanTL-GOB-ES/t5-base-spanish")
except Exception as e:
    # No queremos interrumpir la ejecución por un modelo privado/no encontrado.
    print()
    print("⚠️ No se pudo cargar 'PlanTL-GOB-ES/t5-base-spanish'.")
    print("  Motivo:", str(e).splitlines()[0])
    print("  Esto suele ocurrir si el modelo es privado o si no has iniciado sesión en Hugging Face (hf auth login)")
    print("  Se intentará un modelo público de fallback (google/flan-t5-small). Si quieres usar el modelo oficial, autentícate con 'huggingface-cli login' o proporciona un token.")
    print()
    try:
        text_gen = pipeline(
            "text2text-generation",
            model="google/flan-t5-small",
            device=device_id
        )
        print("✅ Modelo de texto cargado correctamente (fallback): google/flan-t5-small")
    except Exception as e2:
        print()
        print("❌ Error al cargar el modelo de fallback:", e2)
        print("Asegúrate de tener conexión a Internet y de que los paquetes 'transformers' y 'huggingface_hub' estén actualizados.")
        raise

# --- Modelo de imagen ---
print("Cargando modelo de imagen (Stable Diffusion v1-5)...")
model_id = "runwayml/stable-diffusion-v1-5"
scheduler = EulerDiscreteScheduler.from_pretrained(model_id, subfolder="scheduler")

image_gen = StableDiffusionPipeline.from_pretrained(
    model_id,
    scheduler=scheduler,
    torch_dtype=dtype,
    safety_checker=None
)
image_gen.to(device)
print("✅ Modelo de imagen cargado correctamente.")

# --- Función principal ---
def generar_anuncio_y_imagen(descripcion):
    # Prompt de texto
    prompt_text = (
        f"Redacta un anuncio breve y convincente en español para vender el siguiente coche de segunda mano: "
        f"{descripcion}. El texto debe ser natural, atractivo y confiable."
    )

    # Generar texto
    resultado = text_gen(prompt_text, max_new_tokens=120)[0]["generated_text"].strip()
    yield resultado, None

    # Prompt de imagen
    prompt_img = (
        f"fotografía realista de un coche {descripcion}, "
        f"aparacado en una calle moderna, luz natural, fondo urbano, alta calidad, 4K"
    )
    negative_prompt = "borroso, deforme, mala calidad, caricatura, dibujo, texto, marca de agua"

    # Generar imagen
    image = image_gen(
        prompt_img,
        negative_prompt=negative_prompt,
        num_inference_steps=35,
        guidance_scale=7.5
    ).images[0]

    yield resultado, image


# --- Interfaz con Gradio ---
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("## 🚗 Generador de anuncios de coches de segunda mano")

    with gr.Row():
        with gr.Column(scale=1):
            inp_descripcion = gr.Textbox(
                lines=3,
                placeholder="Ejemplo: Mini Cooper Cabrio rojo 2019, 60.000 km, excelente estado",
                label="Descripción del coche"
            )
            btn_generar = gr.Button("Generar Anuncio", variant="primary")

        with gr.Column(scale=1):
            out_texto = gr.Textbox(label="📝 Anuncio generado", lines=8, interactive=False)
            out_imagen = gr.Image(label="🖼️ Imagen generada", interactive=False)

    btn_generar.click(fn=generar_anuncio_y_imagen, inputs=inp_descripcion, outputs=[out_texto, out_imagen])

demo.launch(share=True)
