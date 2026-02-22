#!/bin/bash
#
# Solución rápida para instalar dependencias faltantes
# Usar antes de ejecutar el instalador CUDA principal
#

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🔧 Instalando dependencias básicas para diagnóstico CUDA...${NC}"

# Instalar lspci y otras utilidades de sistema
echo -e "${YELLOW}📦 Instalando pciutils, lsb-release...${NC}"
sudo apt update
sudo apt install -y pciutils lsb-release

# Verificar que lspci funciona ahora
if command -v lspci >/dev/null 2>&1; then
    echo -e "${GREEN}✅ lspci instalado correctamente${NC}"
    
    # Mostrar GPUs detectadas
    echo -e "${CYAN}🎮 GPUs detectadas:${NC}"
    lspci | grep -i vga
    lspci | grep -i nvidia
else
    echo -e "${RED}❌ Error instalando lspci${NC}"
fi

# Verificar nvidia-smi
if command -v nvidia-smi >/dev/null 2>&1; then
    echo -e "${GREEN}✅ nvidia-smi disponible${NC}"
    echo -e "${CYAN}📊 Información de GPU:${NC}"
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits
else
    echo -e "${YELLOW}⚠️ nvidia-smi no disponible${NC}"
fi

# Verificar CUDA existente
if command -v nvcc >/dev/null 2>&1; then
    echo -e "${GREEN}✅ CUDA Toolkit detectado:${NC}"
    nvcc --version | grep "release"
else
    echo -e "${YELLOW}⚠️ CUDA Toolkit no detectado${NC}"
fi

echo ""
echo -e "${GREEN}✅ Dependencias básicas instaladas${NC}"
#!/bin/bash
#
# Script especializado para instalar CUDA + cuDNN para faster-whisper
# Soluciona el problema: "Unable to load libcudnn_ops.so"
# Compatible con Ubuntu 22.04/24.04 y RTX 30xx/40xx
#
# Uso: 
#   chmod +x instalar_cuda.sh
#   ./instalar_cuda.sh
#

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Instalador CUDA + cuDNN para faster-whisper${NC}"
echo -e "${BLUE}===============================================${NC}"

# Verificar que no se ejecute como root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}❌ No ejecutes este script como root${NC}"
    exit 1
fi

# Detectar GPU NVIDIA
detect_gpu() {
    echo -e "${CYAN}🔍 Detectando GPU NVIDIA...${NC}"
    
    if ! lspci | grep -i nvidia >/dev/null 2>&1; then
        echo -e "${RED}❌ No se detectó GPU NVIDIA${NC}"
        exit 1
    fi
    
    if command -v nvidia-smi >/dev/null 2>&1; then
        echo -e "${GREEN}✅ GPU NVIDIA detectada:${NC}"
        nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits
    else
        echo -e "${YELLOW}⚠️ nvidia-smi no disponible. Instalando drivers...${NC}"
        install_nvidia_drivers
    fi
}

# Instalar drivers NVIDIA si no están
install_nvidia_drivers() {
    echo -e "${CYAN}🔧 Instalando drivers NVIDIA...${NC}"
    
    sudo apt update
    sudo apt install -y ubuntu-drivers-common
    
    # Detectar driver recomendado
    recommended_driver=$(ubuntu-drivers devices | grep recommended | awk '{print $3}')
    
    if [ -n "$recommended_driver" ]; then
        echo -e "${BLUE}📦 Instalando driver recomendado: $recommended_driver${NC}"
        sudo apt install -y "$recommended_driver"
    else
        echo -e "${BLUE}📦 Instalando driver genérico...${NC}"
        sudo apt install -y nvidia-driver-535
    fi
    
    echo -e "${YELLOW}⚠️ Se requiere reinicio para cargar los drivers${NC}"
    echo -e "${YELLOW}⚠️ Después del reinicio, ejecuta nuevamente este script${NC}"
    
    read -p "$(echo -e ${CYAN}¿Reiniciar ahora? [Y/n]: ${NC})" restart_choice
    if [[ $restart_choice =~ ^[Yy]$ ]] || [[ -z $restart_choice ]]; then
        sudo reboot
    else
        echo -e "${RED}❌ Reinicia manualmente y ejecuta el script de nuevo${NC}"
        exit 1
    fi
}

# Detectar distribución Ubuntu
detect_ubuntu_version() {
    echo -e "${CYAN}🔍 Detectando versión de Ubuntu...${NC}"
    
    if ! command -v lsb_release >/dev/null 2>&1; then
        sudo apt update && sudo apt install -y lsb-release
    fi
    
    DISTRO=$(lsb_release -si)
    VERSION=$(lsb_release -sr)
    CODENAME=$(lsb_release -sc)
    
    echo -e "${BLUE}📋 Sistema detectado: $DISTRO $VERSION ($CODENAME)${NC}"
    
    # Mapear versión para repositorio CUDA
    case $VERSION in
        "22.04")
            CUDA_REPO="ubuntu2204"
            ;;
        "24.04")
            CUDA_REPO="ubuntu2404"
            ;;
        "20.04")
            CUDA_REPO="ubuntu2004"
            ;;
        *)
            echo -e "${YELLOW}⚠️ Versión no probada. Usando ubuntu2204...${NC}"
            CUDA_REPO="ubuntu2204"
            ;;
    esac
    
    echo -e "${GREEN}✅ Repositorio CUDA: $CUDA_REPO${NC}"
}

# Limpiar instalaciones previas problemáticas
cleanup_previous_cuda() {
    echo -e "${CYAN}🧹 Limpiando instalaciones CUDA problemáticas...${NC}"
    
    # Remover paquetes CUDA conflictivos
    sudo apt remove --purge -y \
        cuda-* \
        nvidia-cuda-* \
        libcudnn* \
        libnvidia-* 2>/dev/null || true
    
    # Limpiar repositorios antiguos
    sudo rm -f /etc/apt/sources.list.d/cuda*.list
    sudo rm -f /etc/apt/trusted.gpg.d/cuda*.gpg
    sudo rm -f /usr/share/keyrings/cuda*.gpg
    
    sudo apt autoremove -y
    sudo apt autoclean
    
    echo -e "${GREEN}✅ Limpieza completada${NC}"
}

# Instalar CUDA Toolkit
install_cuda_toolkit() {
    echo -e "${CYAN}🚀 Instalando CUDA Toolkit 12.6...${NC}"
    
    # Agregar repositorio oficial de NVIDIA
    echo -e "${BLUE}📥 Configurando repositorio NVIDIA...${NC}"
    
    wget -q -O /tmp/cuda-keyring.deb \
        https://developer.download.nvidia.com/compute/cuda/repos/${CUDA_REPO}/x86_64/cuda-keyring_1.1-1_all.deb
    
    sudo dpkg -i /tmp/cuda-keyring.deb
    rm -f /tmp/cuda-keyring.deb
    
    sudo apt update
    
    # Instalar CUDA específico
    echo -e "${BLUE}📦 Instalando CUDA 12.6...${NC}"
    sudo apt install -y \
        cuda-toolkit-12-6 \
        cuda-runtime-12-6 \
        cuda-drivers
    
    echo -e "${GREEN}✅ CUDA Toolkit instalado${NC}"
}

# Instalar cuDNN específico
install_cudnn() {
    echo -e "${CYAN}🧠 Instalando cuDNN 9.1.0...${NC}"
    
    # Método 1: Desde repositorio APT (más confiable)
    echo -e "${BLUE}📦 Instalando cuDNN desde repositorio...${NC}"
    sudo apt install -y \
        libcudnn9-cuda-12 \
        libcudnn9-dev-cuda-12 \
        libcudnn9-samples-cuda-12
    
    # Verificar instalación
    if ldconfig -p | grep -q libcudnn; then
        echo -e "${GREEN}✅ cuDNN instalado correctamente${NC}"
        ldconfig -p | grep cudnn | head -3
    else
        echo -e "${YELLOW}⚠️ Instalación APT falló. Intentando instalación manual...${NC}"
        install_cudnn_manual
    fi
}

# Instalar cuDNN manualmente si APT falla
install_cudnn_manual() {
    echo -e "${CYAN}🔧 Instalación manual de cuDNN...${NC}"
    
    # URLs para cuDNN 9.1.0
    CUDNN_VERSION="9.1.0"
    CUDA_VERSION="12.x"
    
    echo -e "${YELLOW}⚠️ Descarga manual requerida desde NVIDIA:${NC}"
    echo -e "${BLUE}1. Ve a: https://developer.nvidia.com/cudnn${NC}"
    echo -e "${BLUE}2. Regístrate/inicia sesión${NC}"
    echo -e "${BLUE}3. Descarga: cuDNN v${CUDNN_VERSION} para CUDA ${CUDA_VERSION}${NC}"
    echo -e "${BLUE}4. Guarda el archivo en: /tmp/cudnn.tar.xz${NC}"
    
    read -p "$(echo -e ${CYAN}¿Has descargado cuDNN? [y/N]: ${NC})" downloaded
    
    if [[ $downloaded =~ ^[Yy]$ ]]; then
        if [ -f "/tmp/cudnn.tar.xz" ]; then
            echo -e "${BLUE}📦 Instalando cuDNN manualmente...${NC}"
            
            cd /tmp
            tar -xf cudnn.tar.xz
            
            sudo cp cudnn-*-archive/include/cudnn*.h /usr/local/cuda/include 
            sudo cp -P cudnn-*-archive/lib/libcudnn* /usr/local/cuda/lib64 
            sudo chmod a+r /usr/local/cuda/include/cudnn*.h /usr/local/cuda/lib64/libcudnn*
            
            echo -e "${GREEN}✅ cuDNN instalado manualmente${NC}"
        else
            echo -e "${RED}❌ Archivo cuDNN no encontrado en /tmp/cudnn.tar.xz${NC}"
        fi
    fi
}

# Configurar variables de entorno
configure_environment() {
    echo -e "${CYAN}⚙️ Configurando variables de entorno...${NC}"
    
    # Configurar CUDA paths
    cat >> ~/.bashrc << 'EOF'

# === CUDA Configuration for faster-whisper ===
export CUDA_HOME=/usr/local/cuda
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

# cuDNN paths
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Optimizaciones CUDA
export CUDA_LAUNCH_BLOCKING=0
export CUDA_CACHE_DISABLE=0

EOF

    # Crear ldconfig para cuDNN
    echo "/usr/local/cuda/lib64" | sudo tee /etc/ld.so.conf.d/cuda.conf >/dev/null
    sudo ldconfig
    
    # Aplicar cambios inmediatamente
    export CUDA_HOME=/usr/local/cuda
    export PATH=$CUDA_HOME/bin:$PATH
    export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH
    
    echo -e "${GREEN}✅ Variables de entorno configuradas${NC}"
}

# Instalar PyTorch con CUDA correcto
install_pytorch_cuda() {
    echo -e "${CYAN}🔥 Actualizando PyTorch para CUDA 12.6...${NC}"
    
    # Activar entorno virtual si existe
    if [ -d "venv_audio" ]; then
        source venv_audio/bin/activate
        echo -e "${BLUE}🐍 Entorno virtual activado${NC}"
    fi
    
    # Desinstalar versión incorrecta
    pip uninstall -y torch torchaudio
    
    # Instalar versión compatible con CUDA 12.x
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
    
    # Reinstalar faster-whisper
    pip uninstall -y faster-whisper
    pip install faster-whisper
    
    echo -e "${GREEN}✅ PyTorch con CUDA actualizado${NC}"
}

# Verificar instalación completa
# Modo diagnóstico mejorado
run_diagnostics() {
    echo -e "${CYAN}🧪 Verificando instalación CUDA...${NC}"
    
    # Test 1: NVIDIA SMI
    echo -e "${BLUE}📊 Test nvidia-smi:${NC}"
    if nvidia-smi >/dev/null 2>&1; then
        nvidia-smi --query-gpu=name,memory.total,temperature.gpu --format=csv,noheader,nounits
        echo -e "${GREEN}✅ nvidia-smi funcional${NC}"
    else
        echo -e "${RED}❌ nvidia-smi falló${NC}"
    fi
    
    # Test 2: CUDA compiler
    echo -e "${BLUE}🔧 Test nvcc:${NC}"
    if command -v nvcc >/dev/null 2>&1; then
        nvcc --version | grep "release"
        echo -e "${GREEN}✅ CUDA compiler disponible${NC}"
    else
        echo -e "${RED}❌ nvcc no encontrado${NC}"
    fi
    
    # Test 3: cuDNN libraries
    echo -e "${BLUE}📚 Test cuDNN:${NC}"
    if ldconfig -p | grep -q libcudnn; then
        ldconfig -p | grep cudnn | wc -l | xargs echo "Librerías cuDNN encontradas:"
        echo -e "${GREEN}✅ cuDNN libraries disponibles${NC}"
    else
        echo -e "${RED}❌ cuDNN libraries no encontradas${NC}"
    fi
    
    # Test 4: PyTorch CUDA
    if [ -d "venv_audio" ]; then
        source venv_audio/bin/activate
        echo -e "${BLUE}🔥 Test PyTorch CUDA:${NC}"
        python3 -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA version: {torch.version.cuda}')
    print(f'GPU count: {torch.cuda.device_count()}')
    print(f'GPU name: {torch.cuda.get_device_name(0)}')
    # Test simple
    x = torch.tensor([1.0]).cuda()
    print(f'GPU tensor test: {x.device}')
else:
    print('⚠️ CUDA no disponible en PyTorch')
"
        echo -e "${GREEN}✅ PyTorch CUDA test completado${NC}"
    fi
    
    # Test 5: faster-whisper específico
    if [ -d "venv_audio" ]; then
        echo -e "${BLUE}🎙️ Test faster-whisper CUDA:${NC}"
        python3 -c "
try:
    from faster_whisper import WhisperModel
    
    # Intentar cargar modelo en GPU
    model = WhisperModel('tiny', device='cuda', compute_type='float16')
    print('✅ faster-whisper puede usar CUDA')
    del model
    
except Exception as e:
    print(f'❌ Error en faster-whisper: {e}')
    print('🔄 Intentando CPU fallback...')
    try:
        model = WhisperModel('tiny', device='cpu')
        print('✅ faster-whisper funciona en CPU')
        del model
    except Exception as e2:
        print(f'❌ Error también en CPU: {e2}')
"
    fi
}

# Función principal
main() {
    echo -e "${BLUE}🚀 Iniciando instalación CUDA + cuDNN...${NC}"
    
    detect_gpu
    detect_ubuntu_version
    cleanup_previous_cuda
    install_cuda_toolkit
    install_cudnn
    configure_environment
    install_pytorch_cuda
    verify_cuda_installation
    
    echo ""
    echo -e "${GREEN}🎉 ¡Instalación CUDA completada!${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo -e "${CYAN}🔄 Próximos pasos:${NC}"
    echo -e "  ${YELLOW}1.${NC} Reinicia la terminal: ${BLUE}source ~/.bashrc${NC}"
    echo -e "  ${YELLOW}2.${NC} Activa entorno: ${BLUE}source venv_audio/bin/activate${NC}"
    echo -e "  ${YELLOW}3.${NC} Prueba el script: ${BLUE}python you2dl_optimizado.py${NC}"
    echo ""
    echo -e "${CYAN}🐛 Si persisten errores:${NC}"
    echo -e "  ${BLUE}• Reinicia el sistema completamente${NC}"
    echo -e "  ${BLUE}• Verifica que nvidia-smi funcione${NC}"
    echo -e "  ${BLUE}• Ejecuta el test de verificación${NC}"
    echo ""
    echo -e "${GREEN}✨ faster-whisper debería funcionar con GPU ahora${NC}"
}

# Ejecutar
