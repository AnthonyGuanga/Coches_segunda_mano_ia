# -*- coding: utf-8 -*-
#
# Archivo de ejemplo que combina Gradio y un modelo de Hugging Face (Transformers)
# para realizar Transcripción (ASR) y Diarización (estructura de resultados).
#
# Para ejecutar esta aplicación, asegúrate de tener instaladas las librerías:
# pip install gradio transformers
#
# Se recomienda usar el modelo 'openai/whisper-small' o superior para mejor calidad.

import gradio as gr
from transformers import pipeline


# --- CONFIGURACIÓN DEL MODELO DE HUGGING FACE ---

# 1. Cargamos el pipeline de Reconocimiento Automático del Habla (ASR)
print("Cargando el pipeline de Transcripción (ASR) de Hugging Face...")
try:
    # Usamos Whisper Small, un modelo robusto y multilingüe para ASR.
    # El modelo se descargará automáticamente la primera vez.
    asr_pipeline = pipeline("automatic-speech-recognition", model="openai/whisper-small")
    print("Pipeline de ASR cargado exitosamente.")
except Exception as e:
    print(f"Error al cargar el pipeline de ASR: {e}")
    # Detenemos la ejecución si falla la carga crítica del modelo.
    raise RuntimeError("No se pudo inicializar el pipeline de Hugging Face. Verifica tus dependencias y conexión.")


# --- FUNCIÓN PRINCIPAL DE PROCESAMIENTO ---

def procesar_audio(audio_file_path):
    """
    Toma la ruta de un archivo de audio, lo transcribe y genera una salida
    estructurada que simula el resultado de la diarización.

    :param audio_file_path: Ruta al archivo de audio temporal proporcionado por Gradio.
    :return: (str, str) La transcripción pura y la transcripción diarizada (simulada).
    """
    if audio_file_path is None:
        return "ERROR: No se subió ningún archivo de audio.", "Por favor, sube un archivo de audio para comenzar el análisis."

    # --- Tarea 1: Transcripción (ASR) ---
    print(f"Iniciando transcripción para el archivo: {audio_file_path}")
    try:
        # El pipeline ASR devuelve un diccionario con la clave 'text'.
        resultado_transcripcion = asr_pipeline(audio_file_path)
        transcripcion_pura = resultado_transcripcion['text'].strip()
    except Exception as e:
        print(f"Error durante la transcripción: {e}")
        return "ERROR en la Transcripción.", f"Ocurrió un error al procesar el audio: {e}"

    if not transcripcion_pura:
        return "Transcripción Vacía.", "El modelo no pudo detectar voz en el audio subido. Intenta con otro archivo."

    # --- Tarea 2: Diarización (Estructura Simulada) ---
    # En una aplicación real, se usaría un segundo modelo (ej. Pyannote)
    # que devuelve segmentos de texto con etiquetas de tiempo y de orador.
    # Aquí, generamos una simulación que demuestra el formato de salida requerido.

    texto_para_simular_diarizacion = transcripcion_pura

    # Dividimos el texto en párrafos para simular el cambio de orador
    parrafos = texto_para_simular_diarizacion.split('.')
    diarizacion_simulada = []
    
    # Asignamos un orador de forma alternada a cada frase/párrafo
    speaker_map = {0: "Interlocutor 1 (Simulado)", 1: "Interlocutor 2 (Simulado)"}
    
    for i, parrafo in enumerate(parrafos):
        if parrafo.strip():
            speaker = speaker_map[i % 2]
            # Usamos un timestamp ficticio para el ejemplo
            timestamp_simulado = f"[00:{i*5:02d} - 00:{(i*5)+4:02d}]" 
            diarizacion_simulada.append(f"**{timestamp_simulado} {speaker}:** {parrafo.strip()}.")

    diarizacion_final = (
        "--- DIARIZACIÓN DE VOZ (RESULTADO ESTRUCTURADO) ---\n\n"
        "**[INFO]:** La diarización se ha simulado. Un sistema real segmentaría el audio y etiquetaría a cada hablante con precisión.\n\n" +
        "\n\n".join(diarizacion_simulada)
    )

    return transcripcion_pura, diarizacion_final

# --- INTERFAZ DE GRADIO ---

with gr.Blocks(title="ASR y Diarización con Gradio y Hugging Face") as interfaz:
    gr.Markdown(
        """
        # 🎙️ Transcripción y Diarización (Simulada) con Hugging Face
        Esta aplicación demuestra dos tareas de IA aplicadas al audio:
        1. **Transcripción (ASR):** Convierte el audio subido a texto usando el modelo **Whisper Small**.
        2. **Diarización:** Muestra el resultado de la transcripción estructurado para simular la separación de voces y tiempos.
        """
    )

    # Componente de entrada: Subir archivo de audio
    audio_input = gr.Audio(
        type="filepath",
        label="Sube un Archivo de Audio (mp3, wav, flac)",
        sources=["upload", "microphone"] # Permite subir o grabar
    )

    # Componentes de salida
    with gr.Row():
        transcripcion_output = gr.Textbox(
            label="1. Transcripción Pura (ASR)",
            lines=10,
            show_copy_button=True
        )
        diarizacion_output = gr.Markdown(
            label="2. Diarización Estructurada (Simulada)",
            value="Aquí aparecerá la transcripción con el formato de diarización."
        )

    # Botón de procesamiento
    process_button = gr.Button("🚀 Iniciar Transcripción y Análisis")

    # Definimos la acción del botón
    process_button.click(
        fn=procesar_audio,
        inputs=audio_input,
        outputs=[transcripcion_output, diarizacion_output]
    )

if __name__ == "__main__":
    print("Iniciando la interfaz Gradio...")
    interfaz.launch(share=False)