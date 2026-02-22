# 🎵 YOU2DL OPTIMIZADO - Procesamiento de Audio de Alta Velocidad (WSL2/Linux)

Este proyecto es una herramienta avanzada de línea de comandos diseñada específicamente para **WSL2 (Windows Subsystem for Linux)** y entornos **Linux**, optimizada para la descarga, transcripción y procesamiento de audio y video a alta velocidad.

## 🚀 Características Principales

*   **Descarga Ultra-Rápida**: Utiliza `yt-dlp` en su versión *nightly* con optimizaciones personalizadas, logrando descargas hasta **3x más rápidas**.
*   **Transcripción Acelerada**: Implementa **`faster-whisper`**, un motor de transcripción hasta **4x más rápido** que el Whisper original de OpenAI, con soporte para GPU (CUDA) y fallback automático a Whisper estándar si es necesario.
*   **Separación de Voz (Vocal Remover)**: Integración con **Demucs** (modelo `htdemucs_ft`) para extraer voces de alta calidad de cualquier pista de audio.
*   **Inyección de Cookies Nativa**: Sistema inteligente que extrae cookies directamente de **Chromium** en WSL2 para acceder a contenido con restricción de edad, premium o que requiere inicio de sesión (YouTube, TikTok, etc.).
*   **Modo Seguro Anti-Baneo**: Detección automática de *Rate-Limits* y pausas inteligentes para evitar bloqueos de IP durante la descarga de listas de reproducción grandes.
*   **Gestión de Subtítulos**:
    *   Descarga de subtítulos oficiales.
    *   Generación automática con Whisper.
    *   Traducción automática de subtítulos a otros idiomas.
*   **Procesamiento Paralelo**: Capacidad para procesar múltiples archivos simultáneamente utilizando todos los núcleos disponibles de la CPU.
*   **Transcripción Unificada**: Opción exclusiva para combinar múltiples transcripciones en un solo archivo de texto (ideal para datasets o resúmenes largos).

## 📋 Requisitos del Sistema

Este script está optimizado para **Ubuntu 20.04/22.04+** corriendo bajo **WSL2** en Windows 10/11, o cualquier distribución Linux moderna.

### Dependencias del Sistema
*   **Python 3.8+**
*   **FFmpeg**: Esencial para la conversión de audio y video.
*   **Chromium Browser**: Necesario para la gestión de cookies e inicio de sesión.
*   **Deno**: Motor JS requerido por algunas extracciones avanzadas de `yt-dlp`.

## 🛠️ Instalación

### Método Recomendado (Automático)

El proyecto incluye un script de instalación optimizado que configura todo el entorno, incluyendo dependencias del sistema, Python y soporte para GPU (CUDA).

1.  Clona o descarga este repositorio.
2.  Da permisos de ejecución al script instalador:
    ```bash
    chmod +x instalar.sh
    ```
3.  Ejecuta el instalador:
    ```bash
    ./instalar.sh
    ```
    *El script detectará automáticamente si tienes una GPU NVIDIA y te ofrecerá instalar los controladores y librerías CUDA necesarios.*

### Método Manual

Si prefieres instalar las dependencias manualmente:

1.  Instala las dependencias del sistema (Ubuntu/Debian):
    ```bash
    sudo apt update
    sudo apt install ffmpeg chromium-browser python3-pip python3-venv
    ```
    *Asegúrate de instalar también [Deno](https://deno.land/).*

2.  Crea un entorno virtual y actívalo:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  Instala las librerías de Python:
    ```bash
    pip install -r requirements.txt
    ```

## 💻 Uso

Para iniciar la herramienta, asegúrate de tener tu entorno virtual activado y ejecuta:

```bash
python3 ytdpl.py
```

### Flujo de Trabajo
1.  **Ingresa la URL**: Pega el enlace del video o lista de reproducción (YouTube, TikTok, etc.).
2.  **Selecciona una Operación**: Elige una de las opciones del menú interactivo.

### Opciones del Menú

| Opción | Descripción |
| :--- | :--- |
| **1. 📹 Descargar video** | Descarga el video en la mejor calidad disponible a la carpeta `downloads/`. |
| **2. 🎵 Descargar MP3** | Extrae el audio en formato MP3 (320kbps) a la carpeta `audio/`. |
| **3. 🗣️ Extraer solo la voz** | Descarga el audio y utiliza **Demucs** para separar y guardar solo la voz en `vocals/`. |
| **4. 📝 Transcribir audio** | Descarga el audio y genera una transcripción de texto en `transcriptions/`.<br>**Nota:** Permite elegir entre modo *Individual* o *Unificado*. |
| **5. 🎵+🗣️ MP3 + Extraer voz** | Combina descarga de MP3 y extracción de voz. |
| **6. 🎵+📝 MP3 + Transcribir** | Combina descarga de MP3 y transcripción. |
| **7. 🗣️+📝 Extraer voz + Transcribir** | Combina extracción de voz y transcripción. |
| **8. 🎵+🗣️+📝 Todo** | Realiza las tres operaciones: MP3, Voz y Transcripción. |
| **9. 📹+📝 Video + Transcribir** | Descarga el video y genera su transcripción. |
| **10. 📝+🌍 Subtítulos + Traducir** | Descarga/Genera subtítulos y los traduce al inglés (configurado por defecto). |
| **11. 🎵+📝+🌍 MP3 + Subs + Trad** | Audio MP3, Subtítulos y Traducción. |
| **12. 📹+📝+🌍 Video + Subs + Trad** | Video, Subtítulos y Traducción. |
| **13. 🌐 Abrir navegador** | Abre una instancia de Chromium para iniciar sesión manualmente en YouTube/TikTok y sincronizar cookies. Útil si las descargas fallan por restricciones de acceso. |

## 📂 Estructura de Carpetas

El script organiza automáticamente los archivos generados en las siguientes carpetas dentro del directorio del proyecto:

*   `downloads/`: Videos descargados (.mp4, .mkv, etc.).
*   `audio/`: Archivos de audio extraídos (.mp3).
*   `transcriptions/`: Archivos de texto con las transcripciones (.txt).
*   `vocals/`: Pistas de voz aisladas extraídas con Demucs.
*   `subtitles/`: Archivos de subtítulos (.srt) originales y traducidos.
*   `logs/`: Registros de operaciones (si aplica).
*   `temp/`: Archivos temporales (se limpian automáticamente).

## 🛡️ Solución de Problemas

### Error de "Sign in to confirm you're not a bot" o "403 Forbidden"
Esto ocurre cuando YouTube detecta tráfico inusual o requiere autenticación.
1.  Selecciona la **Opción 13** en el menú.
2.  Se abrirá Chromium. Inicia sesión en tu cuenta de Google/YouTube.
3.  Reproduce cualquier video para verificar que carga correctamente.
4.  Cierra el navegador. El script capturará las cookies automáticamente.
5.  Vuelve a intentar la descarga.

### Faster-Whisper no funciona
Si `faster-whisper` falla (por ejemplo, por incompatibilidad de CPU antigua), el script hará un *fallback* automático a la librería `whisper` estándar de OpenAI, asegurando que la transcripción se complete aunque sea más lenta.

### Rate-Limits (Baneos Temporales)
Si estás descargando una *playlist* gigante y YouTube te bloquea temporalmente, el script entrará en modo de espera (30 minutos) automáticamente y reanudará la descarga cuando sea seguro.

## 📝 Créditos
Desarrollado para optimizar flujos de trabajo de IA y creación de contenido, integrando las mejores herramientas de código abierto:
*   [yt-dlp](https://github.com/yt-dlp/yt-dlp)
*   [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
*   [Demucs](https://github.com/facebookresearch/demucs)
