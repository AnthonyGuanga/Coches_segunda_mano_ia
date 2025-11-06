# ============================================================
# 🎬 Auto Ad Creator + Subtitulador con Subtítulos Incrustados
# ============================================================

import gradio as gr
from transformers import pipeline
import torch
import os
from moviepy.editor import VideoFileClip
import subprocess

# ============================================================
# 🔊 Función: Transcribir audio
# ============================================================

def transcribe_audio(audio_path):
    try:
        asr = pipeline(
            "automatic-speech-recognition",
            model="openai/whisper-base",
            return_timestamps=True
        )
        result = asr(audio_path)
        text = result["text"]
        segments = result.get("chunks", [])
        return text, segments
    except Exception as e:
        return f"Error durante la transcripción: {str(e)}", []

# ============================================================
# 🎥 Extraer audio del video
# ============================================================

def extract_audio_from_video(video_path):
    try:
        video = VideoFileClip(video_path)
        audio_path = "temp_audio.wav"
        video.audio.write_audiofile(audio_path, verbose=False, logger=None)
        return audio_path
    except Exception as e:
        raise RuntimeError(f"Error extrayendo audio: {str(e)}")

# ============================================================
# 🕒 Generar subtítulos (.srt)
# ============================================================

def format_timestamp(seconds):
    ms = int((seconds % 1) * 1000)
    s = int(seconds) % 60
    m = (int(seconds) // 60) % 60
    h = int(seconds) // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def write_srt(segments, filename="subtitulos.srt"):
    with open(filename, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, start=1):
            start, end = seg["timestamp"]
            text = seg["text"].strip().replace("\n", " ")
            f.write(f"{i}\n{format_timestamp(start)} --> {format_timestamp(end)}\n{text}\n\n")
    return filename

# ============================================================
# 🎨 Incrustar subtítulos en el video (usa ffmpeg)
# ============================================================

def burn_subtitles(video_path, srt_path, output_path="video_subtitulado.mp4"):
    try:
        # Escapa caracteres especiales en rutas
        safe_srt_path = srt_path.replace("\\", "/")
        safe_video_path = video_path.replace("\\", "/")

        command = [
            "ffmpeg",
            "-y",
            "-i", safe_video_path,
            "-vf", f"subtitles={safe_srt_path}:force_style='Fontsize=20,PrimaryColour=&HFFFFFF&'",
            "-c:a", "copy",
            output_path
        ]
        subprocess.run(command, check=True)
        return output_path
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error al incrustar subtítulos: {e}")

# ============================================================
# 🎯 Procesar video completo (transcribir + subtitular + incrustar)
# ============================================================

def process_video(video_path):
    try:
        # 1️⃣ Extraer audio
        audio_path = extract_audio_from_video(video_path)
        # 2️⃣ Transcribir
        text, segments = transcribe_audio(audio_path)
        # 3️⃣ Generar SRT
        srt_path = write_srt(segments)
        # 4️⃣ Incrustar subtítulos
        output_video = burn_subtitles(video_path, srt_path)
        # 5️⃣ Limpiar temporales
        os.remove(audio_path)
        return text, srt_path, output_video
    except Exception as e:
        return f"Error procesando el video: {str(e)}", None, None

# ============================================================
# 🖥️ Interfaz Gradio
# ============================================================

def build_interface():
    with gr.Blocks(title="Auto Ad Creator + Subtitulador") as demo:
        gr.Markdown("# 🚗 Auto Ad Creator + 🎬 Subtitulador con Subtítulos Incrustados")

        with gr.Tab("🎤 Transcripción de audio"):
            audio_input = gr.Audio(label="Sube o graba un audio", type="filepath")
            trans_btn = gr.Button("Transcribir audio")
            transcription_output = gr.Textbox(label="Transcripción")
            trans_btn.click(
                lambda x: transcribe_audio(x)[0],
                inputs=audio_input,
                outputs=transcription_output,
            )

        with gr.Tab("🎬 Subtitular video"):
            video_input = gr.Video(label="Sube un video")
            sub_btn = gr.Button("Subtitular e incrustar subtítulos")
            video_transcription = gr.Textbox(label="📝 Transcripción del video")
            srt_output = gr.File(label="⬇️ Archivo SRT")
            video_output = gr.Video(label="🎞️ Video con subtítulos incrustados")
            sub_btn.click(
                process_video,
                inputs=video_input,
                outputs=[video_transcription, srt_output, video_output],
            )

    return demo

# ============================================================
# 🚀 Ejecutar la app
# ============================================================

demo = build_interface()
demo.launch()