#!/usr/bin/env python3
"""
🎵 YOU2DL OPTIMIZADO - Procesamiento de Audio de Alta Velocidad (VERSIÓN WSL2)
=============================================================================

Script optimizado para:
  🚀 Descargar video/audio directamente (3x más rápido)
  ⚡ Transcribir con faster-whisper (4x más rápido)
  🔄 Procesar múltiples archivos en paralelo (2-8x más rápido)
  🎤 Extraer voces con Demucs optimizado
  🍪 Inyección de Cookies por ruta absoluta (Fijado para WSL2)
  📡 Monitoreo de progreso en TIEMPO REAL (Terminal streaming)
  📝 Crear y traducir subtítulos
  🔓 Bypass manual de CAPTCHAs y Login nativo con Chromium
  🛡️ Integración automática con DENO y versión Nightly
  ⏱️ Protección ANTI-BANEO en Playlists con Detección de Rate-Limit
  🛑 Interrupción en Tiempo Real para Captchas en medio de Playlists (NUEVO)
  🌐 Opción dedicada para abrir el navegador y exportar cookies

Uso: python3 ytdpl.py
"""

import os, sys, subprocess, glob, shutil, time, re, tempfile, json, sqlite3
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import threading
import signal

# Prevenir ejecución como root
if os.geteuid() == 0:
    sys.exit("🚫 No ejecutes este script como root. Usa un usuario normal.")

# === AUTO-INYECCIÓN DE DENO EN EL PATH ===
USER_HOME = Path.home()
deno_path = str(USER_HOME / ".deno" / "bin")
if deno_path not in os.environ.get("PATH", ""):
    os.environ["PATH"] = f"{deno_path}:{os.environ.get('PATH', '')}"

# Importaciones condicionales
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False

# === CONFIGURACIÓN GLOBAL ===
class Colors:
    RED     = "\033[1;31m"
    GREEN   = "\033[1;32m"
    YELLOW  = "\033[1;33m"
    BLUE    = "\033[1;34m"
    MAGENTA = "\033[1;35m"
    CYAN    = "\033[1;36m"
    WHITE   = "\033[1;37m"
    RESET   = "\033[0m"
    BOLD    = "\033[1m"

PROJECT_DIR = Path(__file__).parent.absolute()
COOKIES_DIR = USER_HOME

DOWNLOAD_DIR = PROJECT_DIR / "downloads"
AUDIO_DIR = PROJECT_DIR / "audio"  
TRANSCRIPTIONS_DIR = PROJECT_DIR / "transcriptions"
VOCALS_DIR = PROJECT_DIR / "vocals"
SUBTITLES_DIR = PROJECT_DIR / "subtitles"
LOGS_DIR = PROJECT_DIR / "logs"
TEMP_DIR = PROJECT_DIR / "temp"

for directory in [DOWNLOAD_DIR, AUDIO_DIR, TRANSCRIPTIONS_DIR, VOCALS_DIR, SUBTITLES_DIR, LOGS_DIR, TEMP_DIR]:
    directory.mkdir(exist_ok=True)

CPU_COUNT = mp.cpu_count()
MAX_WORKERS = min(8, CPU_COUNT)

TEMP_FILES = []
PROCESS_ERROR = False
INTERRUPTED = False
CHROMIUM_PROFILES = []
CURRENT_PROFILE_INDEX = 0
TARGET_PLATFORM = None

LANGUAGES = {
    "1": {"code": "es", "name": "Español", "flag": "🇪🇸"},
    "2": {"code": "en", "name": "English", "flag": "🇬🇧"},
    "3": {"code": "fr", "name": "Français", "flag": "🇫🇷"},
    "4": {"code": "de", "name": "Deutsch", "flag": "🇩🇪"},
    "5": {"code": "it", "name": "Italiano", "flag": "🇮🇹"},
    "6": {"code": "pt", "name": "Português", "flag": "🇵🇹"},
    "7": {"code": "ru", "name": "Русский", "flag": "🇷🇺"},
    "8": {"code": "ja", "name": "日本語", "flag": "🇯🇵"},
    "9": {"code": "zh", "name": "中文", "flag": "🇨🇳"},
    "10": {"code": "ar", "name": "العربية", "flag": "🇸🇦"},
}

def signal_handler(signum, frame):
    global INTERRUPTED
    print(f"\n{Colors.YELLOW}⚠️ Interrupción detectada. Limpiando...{Colors.RESET}")
    INTERRUPTED = True
    cleanup_temp_files()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def print_status(message: str, status: str = "info"):
    timestamp = time.strftime("%H:%M:%S")
    if status == "success":
        print(f"{Colors.GREEN}✅ [{timestamp}] {message}{Colors.RESET}")
    elif status == "error":
        print(f"{Colors.RED}❌ [{timestamp}] {message}{Colors.RESET}")
    elif status == "warning":
        print(f"{Colors.YELLOW}⚠️ [{timestamp}] {message}{Colors.RESET}")
    elif status == "info":
        print(f"{Colors.CYAN}ℹ️ [{timestamp}] {message}{Colors.RESET}")
    elif status == "processing":
        print(f"{Colors.BLUE}⚙️ [{timestamp}] {message}{Colors.RESET}")

def cleanup_temp_files():
    global TEMP_FILES
    for temp_file in TEMP_FILES:
        try:
            if os.path.exists(temp_file): os.remove(temp_file)
        except: pass
    TEMP_FILES.clear()

def update_yt_dlp():
    print_status("Actualizando módulo yt-dlp a versión NIGHTLY y componentes EJS/Deno...", "processing")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--user", "-U", "--pre", 
            "yt-dlp[default]", "yt-dlp-ejs", "curl_cffi", "websockets", "--break-system-packages"], 
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print_status("yt-dlp (Nightly) y componentes actualizados", "success")
    except Exception as e:
        print_status(f"Fallo al actualizar silenciosamente. Detalles: {e}", "warning")

def check_dependencies():
    print_status("Verificando dependencias críticas...", "processing")
    if not shutil.which("ffmpeg"):
        print_status("ffmpeg no instalado.", "error")
        sys.exit(1)
    if not (shutil.which("chromium-browser") or shutil.which("chromium")):
        print_status("Chromium no instalado (es vital para WSL2).", "error")
        sys.exit(1)
    if not shutil.which("deno"):
        print_status("⚠️ DENO NO ENCONTRADO. El motor JS es obligatorio.", "warning")
        print_status("👉 Ejecuta esto en tu terminal: curl -fsSL https://deno.land/install.sh | sh", "error")
    print_status("Dependencias críticas verificadas", "success")

def get_next_chromium_profile():
    global CURRENT_PROFILE_INDEX
    if not CHROMIUM_PROFILES:
        profile_dir = str(USER_HOME / "chromium_data_1")
        os.makedirs(os.path.join(profile_dir, "Default"), exist_ok=True)
        return profile_dir
    profile = CHROMIUM_PROFILES[CURRENT_PROFILE_INDEX]
    CURRENT_PROFILE_INDEX = (CURRENT_PROFILE_INDEX + 1) % len(CHROMIUM_PROFILES)
    return profile

def setup_chromium_profiles():
    global CHROMIUM_PROFILES
    for i in range(1, 6):
        profile_dir = USER_HOME / f"chromium_data_{i}"
        cookies_file = profile_dir / "chromium" / "Default" / "Cookies"
        if profile_dir.exists() and cookies_file.exists() and cookies_file.stat().st_size > 0:
            CHROMIUM_PROFILES.append(str(profile_dir))
    if CHROMIUM_PROFILES:
        print_status(f"Configurados {len(CHROMIUM_PROFILES)} perfiles con cookies válidas", "success")
    else:
        CHROMIUM_PROFILES.append(str(USER_HOME / "chromium_data_1"))

def handle_manual_intervention(url: str, reason: str):
    print(f"\n{Colors.RED}⚠️ ATENCIÓN: {reason}{Colors.RESET}")
    open_browser_for_login(url)

def open_browser_for_login(url: str):
    profile_dir = get_next_chromium_profile()
    
    print(f"{Colors.CYAN}⏫ Abriendo Chromium en WSL2 usando perfil: {profile_dir}{Colors.RESET}")
    try:
        subprocess.Popen(["chromium-browser", f"--user-data-dir={profile_dir}", url], 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print_status(f"Error al abrir chromium-browser: {e}", "error")

    print(f"\n{Colors.YELLOW}🛠️ Pasos a seguir en el navegador:{Colors.RESET}")
    print("1. Inicia sesión, resuelve captchas o asegúrate de que el video carga.")
    print("2. Si necesitas exportar cookies (para ComfyUI), usa tu extensión 'Get cookies.txt' ahora.")
    print("3. CIERRA completamente el navegador Chromium cuando termines.")
    
    input(f"\n{Colors.GREEN}👉 Presiona ENTER aquí cuando hayas CERRADO el navegador para continuar...{Colors.RESET}")
    
    print_status("Sincronizando cookies localmente para yt-dlp...", "processing")
    target_dir = Path(profile_dir) / "chromium"
    target_default = target_dir / "Default"
    source_default = Path(profile_dir) / "Default"
    
    try:
        if target_default.exists(): shutil.rmtree(target_default)
        target_dir.mkdir(exist_ok=True)
        if source_default.exists(): shutil.copytree(source_default, target_default)
        print_status("Cookies sincronizadas y listas para usarse.", "success")
    except Exception as e:
        print_status(f"Error sincronizando cookies: {e}", "warning")

def detect_platform(url: str) -> str:
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower: return "YouTube"
    elif "tiktok.com" in url_lower: return "TikTok"
    else: return "Desconocida"

def analyze_profile_cookies(profile_path: Path) -> Dict[str, any]:
    platforms = {'YouTube': {'has_cookies': False}, 'TikTok': {'has_cookies': False}}
    try:
        cookies_db = profile_path / "chromium" / "Default" / "Cookies"
        if not cookies_db.exists() or cookies_db.stat().st_size == 0:
            cookies_db = profile_path / "Default" / "Cookies"
            if not cookies_db.exists(): return platforms
            
        conn = sqlite3.connect(f"file:{cookies_db}?mode=ro", uri=True, timeout=1)
        cursor = conn.cursor()
        
        cursor.execute("SELECT last_access_utc FROM cookies WHERE host_key LIKE '%youtube.com%' LIMIT 1")
        if cursor.fetchone(): platforms['YouTube']['has_cookies'] = True
            
        cursor.execute("SELECT last_access_utc FROM cookies WHERE host_key LIKE '%tiktok.com%' LIMIT 1")
        if cursor.fetchone(): platforms['TikTok']['has_cookies'] = True
        
        conn.close()
    except: pass
    return platforms

def verify_platform_cookies(platform: str) -> bool:
    if not CHROMIUM_PROFILES: return False
    for profile_path in CHROMIUM_PROFILES:
        platforms = analyze_profile_cookies(Path(profile_path))
        if platforms.get(platform, {}).get('has_cookies', False):
            return True
    return False

def handle_rate_limit_pause():
    """Detiene el flujo de la terminal temporalmente para que yt-dlp se pause."""
    print(f"\n\n{Colors.RED}🛑 ¡ALERTA DE RATE-LIMIT (Baneo Temporal) DE YOUTUBE!{Colors.RESET}")
    print(f"{Colors.YELLOW}Estás descargando videos muy rápido. YouTube ha pausado tu sesión.{Colors.RESET}")
    print(f"{Colors.CYAN}El script congelará la descarga durante 30 minutos para evadir el bloqueo...{Colors.RESET}")
    
    total_seconds = 1800  # 30 minutos
    
    for remaining in range(total_seconds, 0, -1):
        sys.stdout.write(f"\r⏳ Enfriando conexión: {remaining // 60:02d}:{remaining % 60:02d} restantes... ")
        sys.stdout.flush()
        time.sleep(1)
        
    print(f"\n\n{Colors.GREEN}▶️ Reanudando proceso...{Colors.RESET}\n")

# === PYTHON NATIVE DOWNLOADERS CON SALIDA EN TIEMPO REAL Y KILL SWITCH ===
def download_video_direct(url: str, extra_options: List[str] = None, safe_mode: bool = False) -> List[str]:
    platform = detect_platform(url)
    print_status(f"Descargando video de {platform}: {url[:50]}...", "processing")
    
    existing_files = set(DOWNLOAD_DIR.glob("*"))
    base_command = [sys.executable, "-m", "yt_dlp", "--restrict-filenames", "--no-overwrites", "--ignore-errors", "--remote-components", "ejs:github", "-o", str(DOWNLOAD_DIR / "%(title)s.%(ext)s")]
    
    if safe_mode:
        base_command.extend(["--sleep-requests", "1", "--sleep-interval", "10", "--max-sleep-interval", "20", "--sleep-subtitles", "5"])
        
    if extra_options: base_command.extend(extra_options)
    
    # Elevado a 10 reintentos por si hay muchos captchas en una misma playlist
    max_retries = 10
    for attempt in range(max_retries + 1):
        command = base_command.copy()
        
        use_cookies = False
        if platform == "TikTok" or (platform == "YouTube" and attempt > 0):
            use_cookies = True
            
        if use_cookies:
            profile = get_next_chromium_profile()
            if profile:
                command.extend(["--cookies-from-browser", f"chromium:{profile}/chromium"])
                if platform == "YouTube":
                    command.extend(["--extractor-args", "youtube:player_client=tv_downgraded,web"])
        else:
            if platform == "YouTube":
                command.extend(["--extractor-args", "youtube:player_client=android,tv"])
                
        command.append(url)
        
        try:
            print(f"\n{Colors.MAGENTA}--- Registro de yt-dlp ---{Colors.RESET}")
            proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, cwd=str(PROJECT_DIR))
            
            output_lines = []
            killed_by_block = False
            for line in proc.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
                output_lines.append(line)
                line_lower = line.lower()
                
                if "rate-limited by youtube" in line_lower:
                    handle_rate_limit_pause()
                
                # NUEVO: Detección INSTANTÁNEA de Bot/Captcha a mitad de playlist
                if "error:" in line_lower and any(k in line_lower for k in ["sign in to confirm", "not a bot", "captcha", "verify you are human", "403 forbidden"]):
                    print(f"\n{Colors.RED}🛑 Bloqueo detectado a mitad de descarga. Pausando proceso para renovar sesión...{Colors.RESET}")
                    proc.terminate()
                    killed_by_block = True
                    break
            
            proc.wait()
            output = "".join(output_lines)
            print(f"{Colors.MAGENTA}--------------------------{Colors.RESET}\n")

            if proc.returncode == 0 and not killed_by_block:
                current_files = set(DOWNLOAD_DIR.glob("*"))
                new_files = list(current_files - existing_files)
                video_files = [f for f in new_files if f.suffix.lower() in ['.mp4', '.mkv', '.webm', '.flv', '.mov']]
                if video_files:
                    video_files.sort(key=lambda f: f.stat().st_mtime)
                    for f in video_files:
                        print_status(f"Video descargado: {f.name}", "success")
                    return [str(f) for f in video_files]
                else:
                    return []
            else:
                error_msg = output.lower()
                
                if attempt == 0 and platform == "YouTube":
                    if any(k in error_msg for k in ["sign in", "private", "age-restricted", "login", "members-only"]):
                        print_status("Video privado o restringido. Inyectando cookies...", "warning")
                        continue
                
                if any(k in error_msg for k in ["sign in to confirm", "not a bot", "captcha", "verify you are human", "403 forbidden"]):
                    if attempt < max_retries:
                        handle_manual_intervention(url, "Bloqueo duro/Captcha detectado. Abriendo navegador.")
                        continue
                        
                print_status(f"Error en descarga. Revisa el registro arriba.", "error")
                break
        except Exception as e:
            print_status(f"Error descargando video: {e}", "error")
            break
    return []

def download_audio_direct(url: str, extra_options: List[str] = None, safe_mode: bool = False) -> List[str]:
    platform = detect_platform(url)
    print_status(f"Descargando audio de {platform}: {url[:50]}...", "processing")
    
    existing_files = set(AUDIO_DIR.glob("*"))
    base_command = [sys.executable, "-m", "yt_dlp", "-x", "--audio-format", "mp3", "--audio-quality", "320k", "--embed-thumbnail", "--add-metadata", "--restrict-filenames", "--no-overwrites", "--ignore-errors", "--remote-components", "ejs:github", "-o", str(AUDIO_DIR / "%(title)s.%(ext)s")]
    
    if safe_mode:
        base_command.extend(["--sleep-requests", "1", "--sleep-interval", "10", "--max-sleep-interval", "20", "--sleep-subtitles", "5"])
        
    if extra_options: base_command.extend(extra_options)
    
    max_retries = 10
    for attempt in range(max_retries + 1):
        command = base_command.copy()
        
        use_cookies = False
        if platform == "TikTok" or (platform == "YouTube" and attempt > 0):
            use_cookies = True
            
        if use_cookies:
            profile = get_next_chromium_profile()
            if profile:
                command.extend(["--cookies-from-browser", f"chromium:{profile}/chromium"])
                if platform == "YouTube":
                    command.extend(["--extractor-args", "youtube:player_client=tv_downgraded,web"])
        else:
            if platform == "YouTube":
                command.extend(["--extractor-args", "youtube:player_client=android,tv"])
                
        command.append(url)
        
        try:
            print(f"\n{Colors.MAGENTA}--- Registro de yt-dlp ---{Colors.RESET}")
            proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, cwd=str(PROJECT_DIR))
            
            output_lines = []
            killed_by_block = False
            for line in proc.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
                output_lines.append(line)
                line_lower = line.lower()
                
                if "rate-limited by youtube" in line_lower:
                    handle_rate_limit_pause()
                    
                if "error:" in line_lower and any(k in line_lower for k in ["sign in to confirm", "not a bot", "captcha", "verify you are human", "403 forbidden"]):
                    print(f"\n{Colors.RED}🛑 Bloqueo detectado a mitad de descarga. Pausando proceso para renovar sesión...{Colors.RESET}")
                    proc.terminate()
                    killed_by_block = True
                    break
            
            proc.wait()
            output = "".join(output_lines)
            print(f"{Colors.MAGENTA}--------------------------{Colors.RESET}\n")

            if proc.returncode == 0 and not killed_by_block:
                current_files = set(AUDIO_DIR.glob("*"))
                new_files = list(current_files - existing_files)
                mp3_files = [f for f in new_files if f.suffix.lower() == '.mp3']
                if mp3_files:
                    mp3_files.sort(key=lambda f: f.stat().st_mtime)
                    for f in mp3_files:
                        print_status(f"Audio descargado: {f.name}", "success")
                    return [str(f) for f in mp3_files]
                else:
                    return []
            else:
                error_msg = output.lower()
                
                if attempt == 0 and platform == "YouTube":
                    if any(k in error_msg for k in ["sign in", "private", "age-restricted", "login", "members-only"]):
                        print_status("Audio privado o restringido. Inyectando cookies...", "warning")
                        continue
                        
                if any(k in error_msg for k in ["sign in to confirm", "not a bot", "captcha", "verify you are human", "403 forbidden"]):
                    if attempt < max_retries:
                        handle_manual_intervention(url, "Bloqueo duro/Captcha detectado. Abriendo navegador.")
                        continue
                        
                print_status(f"Error en descarga. Revisa el registro arriba.", "error")
                break
        except Exception as e:
            print_status(f"Error descargando audio: {e}", "error")
            break
    return []

def download_subtitles_direct(url: str, language: str = "es", safe_mode: bool = False) -> Optional[str]:
    platform = detect_platform(url)
    print_status(f"Descargando subtítulos de {platform} ({language})...", "processing")
    
    command_info = [sys.executable, "-m", "yt_dlp", "--print", "%(title)s", "--no-warnings", url]
    try:
        result_info = subprocess.run(command_info, capture_output=True, text=True, timeout=30)
        video_title = result_info.stdout.strip().replace("/", "_").replace("\\", "_") if result_info.returncode == 0 else f"video_{int(time.time())}"
        video_title = re.sub(r'[<>:"|?*]', '_', video_title)
    except: video_title = f"video_{int(time.time())}"
    
    existing_subs = list(SUBTITLES_DIR.glob(f"{video_title}*.{language}.srt")) or list(SUBTITLES_DIR.glob(f"{video_title}*.srt"))
    if existing_subs: return str(existing_subs[0])
    
    base_command = [sys.executable, "-m", "yt_dlp", "--write-subs", "--write-auto-subs", "--sub-langs", f"{language},en", "--skip-download", "--convert-subs", "srt", "--no-overwrites", "--ignore-errors", "--remote-components", "ejs:github", "-o", str(SUBTITLES_DIR / f"{video_title}.%(ext)s")]
    
    if safe_mode:
        base_command.extend(["--sleep-requests", "1", "--sleep-interval", "10", "--max-sleep-interval", "20", "--sleep-subtitles", "5"])
        
    max_retries = 10
    for attempt in range(max_retries + 1):
        command = base_command.copy()
        
        use_cookies = False
        if platform == "TikTok" or (platform == "YouTube" and attempt > 0):
            use_cookies = True
            
        if use_cookies:
            profile = get_next_chromium_profile()
            if profile:
                command.extend(["--cookies-from-browser", f"chromium:{profile}/chromium"])
                if platform == "YouTube":
                    command.extend(["--extractor-args", "youtube:player_client=tv_downgraded,web"])
        else:
            if platform == "YouTube":
                command.extend(["--extractor-args", "youtube:player_client=android,tv"])
                
        command.append(url)
        
        try:
            print(f"\n{Colors.MAGENTA}--- Registro de yt-dlp ---{Colors.RESET}")
            proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, cwd=str(PROJECT_DIR))
            
            output_lines = []
            killed_by_block = False
            for line in proc.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
                output_lines.append(line)
                line_lower = line.lower()
                
                if "rate-limited by youtube" in line_lower:
                    handle_rate_limit_pause()
                    
                if "error:" in line_lower and any(k in line_lower for k in ["sign in to confirm", "not a bot", "captcha", "verify you are human", "403 forbidden"]):
                    print(f"\n{Colors.RED}🛑 Bloqueo detectado a mitad de descarga. Pausando proceso para renovar sesión...{Colors.RESET}")
                    proc.terminate()
                    killed_by_block = True
                    break
            
            proc.wait()
            output = "".join(output_lines)
            print(f"{Colors.MAGENTA}--------------------------{Colors.RESET}\n")

            if proc.returncode == 0 and not killed_by_block:
                subtitle_patterns = [f"{video_title}*.{language}.srt", f"{video_title}*.srt", f"*{language}*.srt"]
                for pattern in subtitle_patterns:
                    subtitle_files = list(SUBTITLES_DIR.glob(pattern))
                    if subtitle_files:
                        latest_file = max(subtitle_files, key=lambda f: f.stat().st_mtime)
                        print_status(f"Subtítulos descargados: {latest_file.name}", "success")
                        return str(latest_file)
            
            error_msg = output.lower()
            
            if attempt == 0 and platform == "YouTube":
                if any(k in error_msg for k in ["sign in", "private", "age-restricted", "login", "members-only"]):
                    continue
                    
            if any(k in error_msg for k in ["sign in to confirm", "not a bot", "captcha", "verify you are human", "403 forbidden"]):
                if attempt < max_retries:
                    handle_manual_intervention(url, "Bloqueo duro/Captcha detectado. Abriendo navegador.")
                    continue
                    
            print_status("No se pudieron descargar subtítulos del video", "warning")
            break
        except Exception as e:
            print_status(f"Error descargando subtítulos: {e}", "error")
            break
    return None

# === PROCESAMIENTO RESTANTE (WHISPER, DEMUCS, TRANSLATE) ===
def _transcribe_audio_whisper_core(audio_path: str, include_description: bool = False) -> Optional[str]:
    audio_file = Path(audio_path)
    output_file = TRANSCRIPTIONS_DIR / f"{audio_file.stem}.txt"
    if output_file.exists(): return str(output_file)

    # Intento 1: Faster-Whisper (Prioridad)
    try:
        from faster_whisper import WhisperModel
        print_status(f"Usando Faster-Whisper para: {audio_file.name}", "processing")

        # Detección básica de dispositivo (aunque faster-whisper lo maneja, es bueno para el log)
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"

        compute_type = "float16" if device == "cuda" else "int8"

        model = WhisperModel("large-v3", device=device, compute_type=compute_type)
        segments, info = model.transcribe(str(audio_file), beam_size=5)

        final_text = ""
        for segment in segments:
            final_text += segment.text + " "
        final_text = final_text.strip()

        with open(output_file, "w", encoding="utf-8") as f: f.write(final_text)
        print_status(f"Transcripción guardada (Faster-Whisper): {output_file.name}", "success")
        return str(output_file)

    except ImportError:
        print_status("Faster-Whisper no instalado. Intentando fallback a Whisper tradicional...", "warning")
    except Exception as e:
        print_status(f"Error con Faster-Whisper: {e}. Intentando fallback...", "warning")

    # Intento 2: Whisper Tradicional (Fallback)
    try:
        import whisper
        import torch
        print_status(f"Usando Whisper tradicional para: {audio_file.name}", "processing")

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = whisper.load_model("large", device=device)
        result = model.transcribe(str(audio_file), language=None)
        final_text = result["text"].strip()
        with open(output_file, "w", encoding="utf-8") as f: f.write(final_text)
        print_status(f"Transcripción guardada (Whisper): {output_file.name}", "success")
        return str(output_file)
    except Exception as e:
        print_status(f"Error CRÍTICO en transcripción: {e}", "error")
        return None

def transcribe_audio_optimized(audio_path: str, include_description: bool = False) -> Optional[str]:
    return _transcribe_audio_whisper_core(audio_path, include_description)

def translate_subtitle_file(subtitle_path: str, target_lang: str = "en") -> Optional[str]:
    if not TRANSLATOR_AVAILABLE: return None
    try:
        subtitle_file = Path(subtitle_path)
        output_file = subtitle_file.with_stem(f"{subtitle_file.stem}_{target_lang}").with_suffix(".srt")
        if output_file.exists(): return str(output_file)
        
        with open(subtitle_file, "r", encoding="utf-8", errors="ignore") as f: content = f.read()
        blocks = content.strip().split('\n\n')
        translated_blocks = []
        translator = GoogleTranslator(source='auto', target=target_lang)
        
        for block in blocks:
            lines = block.split('\n')
            if len(lines) >= 3:
                translated_text = translator.translate(' '.join(lines[2:]))
                translated_blocks.append(f"{lines[0]}\n{lines[1]}\n{translated_text}\n")
        
        with open(output_file, "w", encoding="utf-8") as f: f.write('\n'.join(translated_blocks))
        print_status(f"Subtítulos traducidos guardados: {output_file.name}", "success")
        return str(output_file)
    except Exception as e:
        print_status(f"Error traduciendo subtítulos: {e}", "error")
        return None

def generate_subtitles_with_whisper(audio_path: str, language: str = "es") -> Optional[str]:
    try:
        import whisper
        import torch
        audio_file = Path(audio_path)
        output_file = SUBTITLES_DIR / f"{audio_file.stem}_{language}.srt"
        if output_file.exists(): return str(output_file)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = whisper.load_model("large", device=device)
        result = model.transcribe(str(audio_file), language=language if language != 'auto' else None, task="transcribe", word_timestamps=False)
        srt_content = []
        for i, segment in enumerate(result["segments"], 1):
            def f_ts(sec): return f"{int(sec//3600):02d}:{int((sec%3600)//60):02d}:{int(sec%60):02d},{int((sec%1)*1000):03d}"
            srt_content.extend([f"{i}", f"{f_ts(segment['start'])} --> {f_ts(segment['end'])}", segment["text"].strip(), ""])
        with open(output_file, "w", encoding="utf-8") as f: f.write("\n".join(srt_content))
        return str(output_file)
    except: return None

def extract_voice_optimized(audio_path: str) -> Optional[str]:
    audio_file = Path(audio_path)
    output_file = VOCALS_DIR / f"{audio_file.stem}_vocals.mp3"
    if output_file.exists(): return str(output_file)

    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        device = "cpu"

    print_status(f"Iniciando separación de voz con Demucs para: {audio_file.name}", "processing")

    command = ["demucs", "--two-stems=vocals", "-n", "htdemucs_ft", "--device", device, "--shifts", "1", "--overlap", "0.25", "--mp3", "--mp3-bitrate", "320", "-o", str(VOCALS_DIR), str(audio_file)]

    try:
        subprocess.run(command, capture_output=True, text=True, timeout=1200, cwd=str(PROJECT_DIR), check=True)

        model_dir = VOCALS_DIR / "htdemucs_ft"

        # Intentar predecir la ruta (Demucs a veces sanea nombres)
        expected_track_dir = model_dir / audio_file.stem
        candidate = expected_track_dir / "vocals.mp3"

        if not candidate.exists():
            # Búsqueda de respaldo en el directorio del modelo
            candidates = list(model_dir.glob("**/vocals.mp3"))
            if candidates:
                candidate = max(candidates, key=lambda f: f.stat().st_mtime)

        if candidate and candidate.exists():
            shutil.move(str(candidate), str(output_file))
            print_status(f"Voces extraídas: {output_file.name}", "success")

            # Limpieza
            try:
                if candidate.parent.exists(): shutil.rmtree(candidate.parent)
                if model_dir.exists() and not any(model_dir.iterdir()): model_dir.rmdir()
            except: pass

            return str(output_file)
        else:
            print_status("Demucs finalizó pero no se encontró el archivo de salida.", "error")

    except subprocess.CalledProcessError as e:
        print_status(f"Error ejecutando Demucs: {e.stderr}", "error")
    except Exception as e:
        print_status(f"Error inesperado en separación de voz: {e}", "error")
    return None

def unify_transcriptions(paths: List[str], keep_individual: bool):
    print_status("Unificando transcripciones...", "processing")
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    unified_file = TRANSCRIPTIONS_DIR / f"transcripcion_unificada_{timestamp}.txt"

    try:
        with open(unified_file, "w", encoding="utf-8") as outfile:
            for t_path in paths:
                try:
                    with open(t_path, "r", encoding="utf-8") as infile:
                        outfile.write(infile.read() + "\n")
                except Exception as e:
                    print_status(f"Error leyendo {t_path}: {e}", "warning")

        print_status(f"Transcripción unificada guardada: {unified_file.name}", "success")

        if not keep_individual:
            for t_path in paths:
                try:
                    os.remove(t_path)
                except Exception as e:
                    print_status(f"No se pudo borrar {t_path}: {e}", "warning")
            print_status("Archivos individuales eliminados.", "info")

    except Exception as e:
        print_status(f"Error al crear archivo unificado: {e}", "error")

def process_single_file(args: Tuple[str, Dict]) -> Dict:
    file_path, operations = args
    results = {'success': False, 'errors': []}
    try:
        file_obj = Path(file_path)
        is_video = file_obj.suffix.lower() in ['.mp4', '.mkv', '.webm', '.flv', '.mov']
        is_audio = file_obj.suffix.lower() in ['.mp3', '.wav', '.m4a', '.flac']
        current_audio_path = file_path if is_audio else None
        
        safe_mode = operations.get('safe_mode', False)
        
        if file_path.startswith('http') and operations.get('download_subtitles', False):
            if operations.get('subtitle_source') == 'download':
                subs = download_subtitles_direct(file_path, operations.get('subtitle_lang', 'es'), safe_mode)
                if subs and operations.get('translate_subtitles', False):
                    translate_subtitle_file(subs, operations.get('target_lang', 'en'))
                results['success'] = True
                return results
            elif operations.get('subtitle_source') == 'generate':
                current_audio_path = download_audio_direct(file_path, safe_mode=safe_mode)
        
        if is_video and (operations.get('extract_voice', False) or operations.get('transcribe', False) or operations.get('generate_subtitles', False)):
            audio_path = AUDIO_DIR / f"{file_obj.stem}.mp3"
            if not audio_path.exists():
                subprocess.run(["ffmpeg", "-y", "-i", str(file_path), "-vn", "-acodec", "libmp3lame", "-q:a", "2", str(audio_path)], capture_output=True)
            current_audio_path = str(audio_path)
            
        if operations.get('subtitle_source') == 'generate' and current_audio_path:
            subs = generate_subtitles_with_whisper(current_audio_path, operations.get('subtitle_lang', 'es'))
            if subs and operations.get('translate_subtitles', False): translate_subtitle_file(subs, operations.get('target_lang', 'en'))
                
        if operations.get('extract_voice', False) and current_audio_path: extract_voice_optimized(current_audio_path)
        if operations.get('transcribe', False) and current_audio_path:
            trans_path = transcribe_audio_optimized(current_audio_path)
            if trans_path:
                results['transcription_path'] = trans_path
        
        results['success'] = True
    except Exception as e: results['errors'].append(str(e))
    return results

def get_user_input():
    config = {}
    
    while True:
        url = input(f"{Colors.CYAN}🔗 Ingresa URL (o presiona ENTER para cargar opciones generales): {Colors.RESET}").strip()
        if not url:
            url = "https://www.youtube.com"
            
        config['url'] = url
        global TARGET_PLATFORM
        TARGET_PLATFORM = detect_platform(url)
        
        if TARGET_PLATFORM in ["YouTube", "TikTok"]:
            has_cookies = verify_platform_cookies(TARGET_PLATFORM)
            if not has_cookies:
                print(f"\n{Colors.YELLOW}⚠️ No se detectaron cookies recientes para {TARGET_PLATFORM}.{Colors.RESET}")
                print(f"{Colors.CYAN}Si necesitas iniciar sesión, selecciona la opción 13 en el siguiente menú.{Colors.RESET}")
        break
            
    print(f"\n{Colors.CYAN}⚙️ Operaciones disponibles:{Colors.RESET}")
    print("  1. 📹 Descargar video")
    print("  2. 🎵 Descargar MP3") 
    print("  3. 🗣️ Extraer solo la voz (Demucs)")
    print("  4. 📝 Transcribir audio")
    print("  5. 🎵+🗣️ MP3 + Extraer voz")
    print("  6. 🎵+📝 MP3 + Transcribir")
    print("  7. 🗣️+📝 Extraer voz + Transcribir")
    print("  8. 🎵+🗣️+📝 MP3 + Voz + Transcribir")
    print("  9. 📹+📝 Video + Transcribir")
    print("  10. 📝+🌍 Crear subtítulos y traducir")
    print("  11. 🎵+📝+🌍 MP3 + Subtítulos + Traducir")
    print("  12. 📹+📝+🌍 Video + Subtítulos + Traducir")
    print("  13. 🌐 Solo abrir navegador (Para Iniciar sesión o Exportar cookies)")
    
    choice = input(f"{Colors.CYAN}Selecciona [1-13]: {Colors.RESET}").strip()
    
    if choice == "13":
        config['operations'] = {
            'download_video': False, 'download_audio': False, 'extract_voice': False, 
            'transcribe': False, 'download_subtitles': False, 'translate_subtitles': False,
            'open_browser': True
        }
        return config
    
    ops_map = {
        "1": (True, False, False, False, False, False),
        "2": (False, True, False, False, False, False),
        "3": (False, True, True, False, False, False),
        "4": (False, True, False, True, False, False),
        "5": (False, True, True, False, False, False),
        "6": (False, True, False, True, False, False),
        "7": (False, True, True, True, False, False),
        "8": (False, True, True, True, False, False),
        "9": (True, False, False, True, False, False),
        "10": (False, False, False, False, True, True),
        "11": (False, True, False, False, True, True),
        "12": (True, False, False, False, True, True),
    }
    
    v, a, e, t, s, ts = ops_map.get(choice, (True, False, False, False, False, False))
    config['operations'] = {
        'download_video': v, 'download_audio': a, 'extract_voice': e, 
        'transcribe': t, 'download_subtitles': s, 'translate_subtitles': ts,
        'open_browser': False
    }

    if choice == "4":
        print(f"\n{Colors.CYAN}📝 Configuración de Transcripción:{Colors.RESET}")
        print("  1. Individual (Un archivo por audio)")
        print("  2. Unificada (Un solo archivo con todo)")
        transcribe_mode = input(f"{Colors.CYAN}Selecciona modo [1-2]: {Colors.RESET}").strip()

        config['operations']['transcribe_mode'] = 'unified' if transcribe_mode == '2' else 'individual'

        if config['operations']['transcribe_mode'] == 'unified':
            keep = input(f"¿Conservar archivos individuales también? [s/N]: ").strip().lower()
            config['operations']['keep_individual'] = keep == 's'
    
    if s:
        print("\n  1. Descargar subtítulos del video \n  2. Generar subtítulos con Whisper")
        config['operations']['subtitle_source'] = 'download' if input("Origen [1-2]: ").strip() == "1" else 'generate'
        config['operations']['subtitle_lang'] = "es"
        if ts: config['operations']['target_lang'] = "en"
        
    config['download_thumbnail'] = input(f"¿Descargar miniaturas? [s/N]: ").strip().lower() == 's'
    config['download_description'] = input(f"¿Descargar descripciones? [s/N]: ").strip().lower() == 's'
    
    print(f"\n{Colors.YELLOW}🛡️ ¿Vas a descargar una lista de reproducción muy grande?{Colors.RESET}")
    safe_mode_choice = input("Activar 'Modo Seguro' (Añade pausas para evitar bloqueos) [S/n]: ").strip().lower()
    config['operations']['safe_mode'] = safe_mode_choice != 'n'
    
    return config

def main():
    try:
        check_dependencies()
        update_yt_dlp()
        setup_chromium_profiles()
        config = get_user_input()
        
        if config.get('operations', {}).get('open_browser'):
            open_browser_for_login(config['url'])
            print(f"\n{Colors.GREEN}🎉 ¡Navegador cerrado y cookies sincronizadas con éxito!{Colors.RESET}")
            return
        
        print(f"\n{Colors.BLUE}🚀 Iniciando procesamiento...{Colors.RESET}")
        
        safe_mode = config['operations'].get('safe_mode', False)
        
        if config['operations']['download_subtitles'] and not config['operations']['download_video'] and not config['operations']['download_audio']:
            process_single_file((config['url'], config['operations']))
        else:
            options = ["--no-overwrites"]
            if config.get('download_thumbnail'): options.append("--write-thumbnail")
            if config.get('download_description'): options.append("--write-description")
            
            files = []
            if config['operations']['download_video']:
                files = download_video_direct(config['url'], options, safe_mode)
            elif config['operations']['download_audio']:
                files = download_audio_direct(config['url'], options, safe_mode)
            
            if files:
                print_status(f"Se procesarán {len(files)} archivos nuevos.", "info")
                transcription_paths = []
                for file in files:
                    result = process_single_file((file, config['operations']))
                    if result.get('transcription_path'):
                        transcription_paths.append(result['transcription_path'])

                if config['operations'].get('transcribe_mode') == 'unified' and transcription_paths:
                    unify_transcriptions(transcription_paths, config['operations'].get('keep_individual', True))
            else:
                print_status("No se descargaron nuevos archivos.", "warning")
            
        print(f"\n{Colors.GREEN}🎉 ¡Procesamiento completado!{Colors.RESET}")
        
    except KeyboardInterrupt: pass
    finally: cleanup_temp_files()

if __name__ == "__main__":
    main()