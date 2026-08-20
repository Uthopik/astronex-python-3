# Instalación de Astro-Nex (Python 3 / GTK3)

## Opción 1: Instalación nativa en Linux

### Ubuntu 22.04 / 24.04 / 26.04 · Debian 12

PyGObject y pycairo se instalan **desde apt** (no con pip: compilarlos falla en
Ubuntu 24.04+). Los runtime de GTK los arrastra `gir1.2-gtk-3.0` con el nombre
correcto de cada versión (en 24.04+ varios cambiaron, p. ej. `libgdk-pixbuf2.0-0`
→ `libgdk-pixbuf-2.0-0`).

```bash
# Paquetes del sistema (válido en 22.04 / 24.04 / 26.04)
sudo apt update
sudo apt install -y \
    python3 python3-pip python3-dev python3-venv \
    python3-gi python3-gi-cairo python3-cairo \
    gir1.2-gtk-3.0 \
    build-essential \
    fonts-dejavu-core fontconfig \
    xdg-utils evince eog
```

### Dependencias Python

Usa un virtualenv con `--system-site-packages` (así reutiliza el PyGObject/
pycairo de apt en vez de recompilarlos):

```bash
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install --use-pep517 -r requirements.txt   # solo compila pyswisseph; el resto son wheels
```

Alternativa (instalación global, si tu distro lo permite):

```bash
pip3 install --break-system-packages --use-pep517 -r requirements.txt
```

### Fuente astrológica (CRÍTICO)

Sin esta fuente no se ven los símbolos de planetas y signos:

```bash
mkdir -p ~/.fonts
cp astronex/resources/Astro-Nex.ttf ~/.fonts/
fc-cache -f -v
```

### Ejecutar

```bash
python3 nex.py
```

### Atajo en menú (opcional)

Para tener Astro-Nex en el menú de aplicaciones:

```bash
mkdir -p ~/.local/share/applications
cat > ~/.local/share/applications/astronex.desktop << 'EOF'
[Desktop Entry]
Name=Astro-Nex
Comment=Cartas astrologicas metodo API
Exec=python3 /ruta/a/astronex/nex.py
Icon=/ruta/a/astronex/astronex/resources/iconex-48.png
Type=Application
Categories=Science;
EOF
```

Reemplaza `/ruta/a/astronex/` por la ruta donde descomprimiste el `.tar.gz`.

---

## Opción 2: Docker (recomendado para WSL2 / Windows)

Útil si no quieres instalar dependencias en tu sistema, o si estás en WSLg.

### Requisitos
- Docker instalado y corriendo
- En Linux nativo: X server activo (Wayland o X11)
- En Windows: WSL2 con WSLg

### Pasos

```bash
cd docker-py3
docker compose up
```

El primer arranque construye la imagen (2-3 min). Las siguientes ejecuciones
son inmediatas.

Para detener: `Ctrl+C` o desde otra terminal `docker compose down`.

### Datos persistentes

Los datos de usuario (cartas, configuración) se guardan en un volumen Docker
llamado `astronex-py3-data`. Persisten entre reinicios. Para hacer backup:

```bash
docker run --rm -v astronex-py3-data:/data -v $(pwd):/backup \
    ubuntu tar czf /backup/astronex-data.tar.gz -C /data .
```

Para restaurar:

```bash
docker run --rm -v astronex-py3-data:/data -v $(pwd):/backup \
    ubuntu tar xzf /backup/astronex-data.tar.gz -C /data
```

### Tema oscuro

Por defecto, el `docker-compose.yml` activa `GTK_THEME=Adwaita:dark`. Si
prefieres tema claro, edita `docker-compose.yml` y elimina o comenta esa línea.

---

## Verificación

Una vez instalado, al ejecutar `python3 nex.py` deberías ver:

1. Splash screen breve
2. Ventana principal con una carta del momento actual cargada
3. Panel izquierdo con lista de cartas, panel derecho con la rueda astrológica
4. Si presionas `Ctrl+B` se abre el Explorador de cartas

Si la rueda muestra signos en formato de caracteres extraños (no símbolos
astrológicos), la fuente `Astro-Nex.ttf` no se instaló correctamente. Repite
el paso de fuente y reinicia.

---

## Problemas conocidos

- **WSLg + título de ventana blanco**: el título de la ventana es decoración
  nativa de Windows y no respeta el tema oscuro de GTK. En Linux con GNOME/KDE
  el WM aplicará el tema correcto.
- **PDF/PNG export con visor `kpdf`**: si tu `cfg.ini` viejo tiene `kpdf`,
  cámbialo a `evince` en Preferencias → PDF.
- **DST México 2022**: la app no maneja correctamente la supresión del horario
  de verano en México. Es limitación conocida del autor original.
