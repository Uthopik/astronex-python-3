#!/bin/bash
# Astro-Nex Python 3 - Script de instalacion express
#
# Uso:
#   bash install.sh            -> instalacion con DOCKER (recomendada)
#   bash install.sh --nativo   -> instalacion NATIVA (sin Docker, Debian/Ubuntu)
#
# Docker: verifica/instala Docker, te anade al grupo, construye y arranca.
# Nativo: instala dependencias del sistema (apt) + entorno Python (venv con
#         --system-site-packages) + la fuente Astro-Nex.ttf, y lanza la app.

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Modo: docker (por defecto) o nativo (--nativo / --native)
MODE="docker"
if [ "$1" = "--nativo" ] || [ "$1" = "--native" ]; then
    MODE="nativo"
fi

# ---------------------------------------------------------------------------
# Instalacion NATIVA (sin Docker). Solo Debian/Ubuntu (apt). Verificado en
# Ubuntu 22.04 / 24.04 / 26.04. PyGObject y pycairo vienen de apt (no se
# compilan con pip); el venv usa --system-site-packages para reutilizarlos.
# ---------------------------------------------------------------------------
native_install() {
    echo -e "${BLUE}=== Astro-Nex - Instalacion NATIVA (sin Docker) ===${NC}"
    echo ""

    if [ ! -f "requirements.txt" ]; then
        echo -e "${RED}ERROR: no encuentro requirements.txt (ejecuta desde la carpeta astronex/).${NC}"
        exit 1
    fi

    if ! command -v apt &> /dev/null; then
        echo -e "${YELLOW}La instalacion nativa automatica solo cubre Debian/Ubuntu (apt).${NC}"
        echo "Para Fedora/Arch instala los equivalentes (gtk3, gobject-introspection,"
        echo "python3-gobject/python-gobject, python3-cairo/python-cairo, base de compilacion)"
        echo "y sigue INSTALACION.md (paso B). Luego:"
        echo "   python3 -m venv --system-site-packages venv"
        echo "   venv/bin/pip install -r requirements.txt"
        exit 1
    fi

    echo -e "${GREEN}[1/4]${NC} Dependencias del sistema (apt)..."
    # OJO: NO se listan los runtime de GTK (libgtk-3, gdk-pixbuf, pango, cairo);
    # los arrastra gir1.2-gtk-3.0 con el nombre correcto de cada version de
    # Ubuntu (en 24.04+ algunos cambiaron, p.ej. libgdk-pixbuf2.0-0 ->
    # libgdk-pixbuf-2.0-0). build-essential es para compilar pyswisseph.
    sudo apt update
    sudo apt install -y \
        python3 python3-pip python3-dev python3-venv \
        python3-gi python3-gi-cairo python3-cairo \
        gir1.2-gtk-3.0 \
        build-essential \
        fonts-dejavu-core fontconfig \
        xdg-utils evince eog

    echo -e "${GREEN}[2/4]${NC} Entorno Python (venv --system-site-packages)..."
    python3 -m venv --system-site-packages venv
    venv/bin/pip install --upgrade pip
    # Reutiliza PyGObject/pycairo de apt; solo compila pyswisseph y baja wheels.
    # --use-pep517: pyswisseph no trae pyproject.toml, evita el aviso de pip
    # sobre el mecanismo legacy setup.py bdist_wheel (que pip ira retirando).
    venv/bin/pip install --use-pep517 -r requirements.txt

    echo -e "${GREEN}[3/4]${NC} Fuente astrologica Astro-Nex.ttf..."
    mkdir -p "$HOME/.fonts"
    cp astronex/resources/Astro-Nex.ttf "$HOME/.fonts/"
    fc-cache -f > /dev/null 2>&1 || true

    echo -e "${GREEN}[4/4]${NC} Creando lanzador ./nex-nativo.sh ..."
    cat > nex-nativo.sh << 'LAUNCH'
#!/bin/bash
# Lanzador de Astro-Nex (instalacion nativa). Generado por install.sh --nativo.
cd "$(dirname "$0")"
exec venv/bin/python3 nex.py
LAUNCH
    chmod +x nex-nativo.sh

    echo ""
    echo -e "${GREEN}=== Instalacion nativa completada ===${NC}"
    echo ""
    echo "Para ejecutar Astro-Nex:"
    echo "   ./nex-nativo.sh"
    echo "   (o:  source venv/bin/activate  &&  python3 nex.py )"
    echo ""

    if [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ]; then
        echo -e "${BLUE}Arrancando Astro-Nex...${NC}"
        exec venv/bin/python3 nex.py
    else
        echo -e "${YELLOW}No hay display detectado (\$DISPLAY vacio): no la arranco ahora.${NC}"
        echo "Ejecuta ./nex-nativo.sh desde tu sesion grafica."
    fi
    exit 0
}

echo -e "${BLUE}=== Astro-Nex Python 3 - Instalador ===${NC}"
echo ""

# 1. Verificar estructura
if [ ! -f "nex.py" ] || [ ! -d "docker" ]; then
    echo -e "${RED}ERROR: No estas en la carpeta correcta.${NC}"
    echo ""
    echo "Debes ejecutar este script desde la carpeta astronex/ (la que se crea"
    echo "al descomprimir el .tar.gz)."
    echo ""
    echo "Asegurate de haber hecho:"
    echo "   tar xzf astronex-py3-v2.1.tar.gz"
    echo "   cd astronex"
    echo "   bash install.sh"
    exit 1
fi

# Si se pidio instalacion nativa, hacerla y salir (no toca Docker).
if [ "$MODE" = "nativo" ]; then
    native_install
fi

echo -e "${GREEN}[1/4]${NC} Carpeta del proyecto detectada correctamente."

# 2. Verificar Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}[2/4] Docker no esta instalado. Instalandolo...${NC}"
    if command -v apt &> /dev/null; then
        sudo apt update
        sudo apt install -y docker.io docker-compose-v2
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y docker docker-compose
    elif command -v pacman &> /dev/null; then
        sudo pacman -Sy --noconfirm docker docker-compose
    else
        echo -e "${RED}ERROR: distribucion no reconocida. Instala Docker manualmente.${NC}"
        echo "Visita https://docs.docker.com/engine/install/"
        exit 1
    fi
    sudo systemctl enable --now docker
else
    echo -e "${GREEN}[2/4]${NC} Docker ya esta instalado: $(docker --version)"
fi

# 3. Verificar que el usuario esta en el grupo docker
if ! groups | grep -q docker; then
    echo -e "${YELLOW}[3/4] Anadiendo tu usuario al grupo docker...${NC}"
    sudo usermod -aG docker $USER

    # En Ubuntu 26.04+ newgrp/sg no vienen preinstalados (movidos a util-linux-extra)
    if ! command -v newgrp &> /dev/null && ! command -v sg &> /dev/null; then
        echo -e "${YELLOW}Instalando util-linux-extra (newgrp/sg)...${NC}"
        if command -v apt &> /dev/null; then
            sudo apt install -y util-linux-extra || true
        fi
    fi

    echo ""
    echo -e "${YELLOW}IMPORTANTE:${NC} Tu usuario fue anadido al grupo docker."
    echo ""
    echo "Opciones para aplicar el cambio (elige UNA):"
    echo ""
    echo "  A) RECOMENDADA - Cerrar sesion completamente y volver a entrar."
    echo "     (Menu de Ubuntu -> Cerrar sesion. Despues vuelve a esta carpeta"
    echo "      y ejecuta: bash install.sh)"
    echo ""
    if command -v newgrp &> /dev/null; then
        echo "  B) Sin cerrar sesion: ejecuta 'newgrp docker' y luego 'bash install.sh'"
    elif command -v sg &> /dev/null; then
        echo "  B) Sin cerrar sesion: ejecuta 'sg docker -c \"bash install.sh\"'"
    fi
    echo ""
    exit 0
else
    echo -e "${GREEN}[3/4]${NC} Tu usuario ya esta en el grupo docker."
fi

# 4. Verificar Docker funciona
if ! docker info &> /dev/null; then
    echo -e "${RED}ERROR: Docker esta instalado pero no funciona.${NC}"
    echo "Verifica que el servicio este corriendo:"
    echo "   sudo systemctl start docker"
    exit 1
fi

echo -e "${GREEN}[4/4]${NC} Docker funcional. Compilando e iniciando Astro-Nex..."
echo ""

# 5. Permitir que Docker acceda al display X11 (necesario en Linux nativo)
if command -v xhost &> /dev/null; then
    xhost +local:docker > /dev/null 2>&1 || xhost +local: > /dev/null 2>&1 || true
    echo "  X11 access concedido a contenedores locales."
fi

# 6. Construir y arrancar
cd docker
docker compose up --build

echo ""
echo -e "${GREEN}=== Astro-Nex se ha cerrado correctamente ===${NC}"
echo ""
echo "Para volver a iniciar:"
echo "   cd $(pwd)"
echo "   docker compose up"
