# -*- coding: utf-8 -*-
#
# Archivo de simulación ESTABLE Y FINAL.
# Se elimina 'transformers.pipeline' y se utiliza el modelo y procesador directos
# para evitar que PyTorch/TorchCodec interfiera con la carga de audio.

import gradio as gr
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import librosa # Obligatorio para la carga robusta del audio
import torch
import os

# --- CONFIGURACIÓN DEL MODELO DE HUGGING FACE (Directo) ---

MODEL_ID = "openai/whisper-small"
SAMPLE_RATE = 16000

print(f"Cargando Procesador y Modelo de Whisper ({MODEL_ID})...")

try:
    # Cargamos el procesador y el modelo de forma explícita
    processor = WhisperProcessor.from_pretrained(MODEL_ID)
    model = WhisperForConditionalGeneration.from_pretrained(MODEL_ID)
    
    # Configuramos el dispositivo (GPU si está disponible, sino CPU)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    print(f"Modelo cargado y utilizando el dispositivo: {device}")
    
except Exception as e:
    print(f"Error al cargar el modelo/procesador: {e}")
    raise RuntimeError("No se pudo inicializar el modelo de Whisper. Verifica tus dependencias y conexión.")


# --- FUNCIÓN PRINCIPAL DE PROCESAMIENTO ---

def procesar_audio(audio_file_path):
    """
    Carga el audio usando librosa, lo procesa con Whisper a bajo nivel y simula la diarización.
    """
    if audio_file_path is None:
        return "ERROR: No se subió ningún archivo de audio.", "Por favor, sube un archivo de audio para comenzar el análisis."

    # --- Tarea 1: Transcripción (ASR) ---
    
    # 1. Carga Robusta de Audio con Librosa (Solución al error libtorchcodec)
    try:
        # Cargamos el audio a un array de NumPy (mono) a 16kHz
        waveform_np, sr = librosa.load(audio_file_path, sr=SAMPLE_RATE)
        
    except Exception as e:
        return f"ERROR en la Carga de Audio (Librosa): {e}", "Ocurrió un error al cargar el archivo de audio. Asegúrate de que es un formato válido."

    # 2. Pre-procesamiento y Transcripción de Bajo Nivel
    print(f"Iniciando transcripción de bajo nivel para el archivo: {audio_file_path}")
    try:
        # Convertimos el array de NumPy en features (Mel Spectrogram)
        input_features = processor(waveform_np, sampling_rate=SAMPLE_RATE, return_tensors="pt").input_features
        
        # Movemos las features al dispositivo correcto (CPU o CUDA)
        input_features = input_features.to(device)
        
        # Generamos la transcripción (token IDs)
        predicted_ids = model.generate(input_features, forced_decoder_ids=processor.get_decoder_prompt_ids(language="es", task="transcribe"))
        
        # Decodificamos los IDs a texto
        transcripcion_pura = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0].strip()
        
    except Exception as e:
        # Este catch debería atrapar errores específicos del modelo, no de carga de audio.
        print(f"Error durante la generación de transcripción (Modelo): {e}")
        return "ERROR en la Transcripción (Modelo).", f"Ocurrió un error al procesar el audio: {e}"

    if not transcripcion_pura:
        return "Transcripción Vacía.", "El modelo no pudo detectar voz en el audio subido. Intenta con otro archivo."

    # --- Tarea 2: Diarización (Estructura Simulada) ---
    
    texto_para_simular_diarizacion = transcripcion_pura

    # Dividimos el texto en frases (usando punto y signo de interrogación)
    delimitadores = ['.', '?', '!', '...']
    parrafos = []
    current_segment = ""
    for char in texto_para_simular_diarizacion:
        current_segment += char
        if char in delimitadores:
            parrafos.append(current_segment.strip())
            current_segment = ""
    if current_segment.strip():
        parrafos.append(current_segment.strip())

    diarizacion_simulada = []
    
    # Asignamos oradores de forma alternada (Vendedor/Cliente)
    speaker_map = {0: "VENDEDOR (Simulado)", 1: "CLIENTE (Simulado)"}
    current_time_sec = 0
    
    for i, parrafo in enumerate(parrafos):
        if parrafo:
            speaker = speaker_map[i % 2]
            # Estimamos la duración del segmento (ficticio)
            duration = min(len(parrafo) // 5, 8) + 2
            
            start_time = _format_time(current_time_sec)
            current_time_sec += duration
            end_time = _format_time(current_time_sec)

            timestamp_simulado = f"[{start_time} - {end_time}]" 
            diarizacion_simulada.append(f"**{timestamp_simulado} {speaker}:** {parrafo.strip()}.")

    diarizacion_final = (
        "--- DIARIZACIÓN DE VOZ (RESULTADO ESTRUCTURADO) ---\n\n"
        "**[INFO]:** ¡ÉXITO! La transcripción funcionó gracias al procesamiento de bajo nivel. La diarización se ha simulado.\n\n" +
        "\n\n".join(diarizacion_simulada)
    )

    return transcripcion_pura, diarizacion_final

def _format_time(seconds: float) -> str:
    """Convierte segundos a formato [MM:SS] o [HH:MM:SS]"""
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"
    return f"{int(m):02d}:{int(s):02d}"


# --- INTERFAZ DE GRADIO ---

with gr.Blocks(title="ASR y Diarización Estable con Modelo Directo") as interfaz:
    gr.Markdown(
        """
        # 🎙️ Transcripción y Diarización (Simulada) - Versión Final
        Esta versión es la **más estable** porque evita la función `pipeline` de Hugging Face que causaba el error de `libtorchcodec`.

        **Proceso (Nivel de Estabilidad Máxima):**
        1. **Carga Segura:** `librosa` carga el audio a un array de NumPy (estable).
        2. **Procesamiento Directo:** El modelo `WhisperForConditionalGeneration` y `WhisperProcessor` trabajan directamente con el array de NumPy, evitando las librerías problemáticas.
        3. **Diarización (Simulada):** El texto se estructura para simular la separación de voces y tiempos.
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