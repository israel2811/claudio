---
title: Claudio - Forensic Audio Recovery
emoji: 🔊
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 4.44.0
app_file: huggingface_app.py
pinned: false
license: mit
---

# Claudio - Forensic Audio Recovery

Recupera voces atenuadas por debajo de -35dB usando amplificación por coherencia de fase.

## Características

- **Amplificación por coherencia de fase**: Usa principios de física de ondas para amplificar señales débiles
- **Realce espectral**: Amplifica frecuencias de voz humana (80-8000 Hz)
- **Boost de formantes**: F1, F2, F3 para claridad vocal
- **Soporte multi-formato**: WAV, MP3, FLAC, OGG, etc.

## Uso

1. Sube un archivo de audio
2. Ajusta el umbral de detección (-35dB por defecto)
3. Configura las iteraciones de amplificación
4. Haz clic en "Procesar Audio"
5. Descarga el audio recuperado

## Cómo funciona

La herramienta utiliza el principio de interferencia constructiva de ondas:
- Crea copias de la señal con fase invertida
- Re-invierte las copias para alinear fases
- Suma las señales para obtener ganancia de amplitud
- Aplica realce espectral en bandas de voz
