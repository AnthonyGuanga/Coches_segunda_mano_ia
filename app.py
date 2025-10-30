# file: app.py
import gradio as gr
from answer_question import answer_question

# Función principal de Gradio
iface = gr.Interface(
    fn=answer_question,
    inputs=gr.Textbox(
        label="Escribe tu pregunta sobre coches o clima",
        placeholder="Ej: Dime el precio de un Seat Ibiza en Valencia",
        lines=4,  # caja grande
        max_lines=10
    ),
    outputs=gr.Textbox(
        label="Respuesta",
        lines=8,  # área de respuesta más grande
        placeholder="Aquí aparecerá la respuesta de Gemini + RAG + tools"
    ),
    title="Asistente Inteligente de Coches",
    description="""
Preguntas de ejemplo:
- Dime el clima de valencia el 2025-11-02
- Quiero saber si puedo probar un coche en Madrid el 2025-11-01
- Dime los recalls de un Onda civic 2018
- Quiero un coche de gasolina por menos de 17000 euros

""",
    allow_flagging="never",
)

if __name__ == "__main__":
    iface.launch(share=True)  # share=True para obtener enlace público temporal
