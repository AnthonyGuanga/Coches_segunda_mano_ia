import gradio as gr
from answer_question import answer_question

with gr.Blocks(theme=gr.themes.Soft(primary_hue="cyan")) as iface:

    with gr.Row():
        gr.Markdown(
            """
            # 🚗 Asistente Inteligente de Coches
            """
        )

    # Entrada y salida
    with gr.Row():
        with gr.Column(scale=2):
            user_input = gr.Textbox(
                label="💬 Escribe tu pregunta",
                placeholder="Ej: Dime el clima de Valencia el 2025-11-02",
                lines=4,
                max_lines=10
            )
            run_btn = gr.Button("🚀 Obtener respuesta", variant="primary")
            examples = gr.Examples(
                examples=[
                    "Dime el clima de valencia el 2025-11-02",
                    "Quiero saber si puedo probar un coche en Madrid el 2025-11-01",
                    "Dime los recalls de un Honda Civic 2018",
                    "Quiero un coche de gasolina por menos de 17000 euros",
                ],
                inputs=user_input
            )

        with gr.Column(scale=3):
            output_box = gr.Textbox(
                label="🧠 Respuesta del asistente",
                lines=12,
                placeholder="Aquí aparecerá la respuesta generada...",
            )

    with gr.Row():
        gr.Markdown(
            "<p style='text-align:center; color:gray;'>Desarrollado con ❤️ por tu Asistente de Coches Inteligente</p>"
        )

    run_btn.click(fn=answer_question, inputs=user_input, outputs=output_box)

if __name__ == "__main__":
    iface.launch(share=True)

