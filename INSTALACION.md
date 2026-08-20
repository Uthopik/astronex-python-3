# Astro-Nex Python 3 — Guía de instalación

> **Versión**: 2.1
> **Plataforma**: Linux (Ubuntu 22.04+ / Debian 12+ / Fedora / Arch)
> **Soporte adicional**: Windows con WSL2 + Docker Desktop

Esta guía explica paso a paso cómo instalar y ejecutar Astro-Nex en Linux. Hay
dos rutas disponibles: **Docker** (recomendada, más simple) e **instalación
nativa** (sin Docker, requiere instalar dependencias del sistema).

---

## Contenido del paquete

Al descomprimir `astronex-py3-v2.1.tar.gz` obtienes la carpeta `astronex/`
con esta estructura:

```
astronex/
├── nex.py                  # Entry point principal
├── pysw.py                 # Wrapper de Swiss Ephemeris
├── requirements.txt        # Dependencias pip
├── setup.py                # Setup tradicional Python
├── README.md               # Información general
├── INSTALL.md              # Instalación tradicional (referencia)
├── INSTALACION.md          # Esta guía
├── astronex/               # Código fuente principal
│   ├── gui/                # Interfaz GTK3
│   ├── drawing/            # Dibujo de cartas (Cairo)
│   ├── surfaces/           # Exportación PNG, PDF, impresión
│   ├── extensions/         # Utilidades varias
│   ├── locale/             # Traducciones (es/en/ca/de)
│   └── resources/          # Iconos, fuente Astro-Nex.ttf, charts.db
├── bin/                    # Script wrapper
└── docker/                 # Configuración Docker
    ├── Dockerfile
    ├── docker-compose.yml
    └── fonts/
```

---

## Ruta A — Instalación con Docker (RECOMENDADA)

### Por qué Docker

- No tocas tu sistema con dependencias nuevas
- Funciona idéntico en cualquier distro Linux
- Si algo se rompe, lo reinstalas en segundos
- Todos los paquetes (Python 3.12, GTK3, fuentes) ya están listos

### A.1 — Requisitos

Asegúrate de tener instalado **Docker** y **Docker Compose**:

```bash
# Ubuntu / Debian
sudo apt update
sudo apt install -y docker.io docker-compose-v2

# Fedora
sudo dnf install -y docker docker-compose

# Arch
sudo pacman -S docker docker-compose

# Después de instalar, añade tu usuario al grupo docker
sudo usermod -aG docker $USER

# IMPORTANTE: cierra sesión y vuelve a entrar (o reinicia) para que tome efecto
```

Verifica que Docker funciona:

```bash
docker --version
docker compose version
docker run --rm hello-world
```

Si `hello-world` muestra el mensaje de bienvenida, estás listo.

### A.2 — Descomprimir el paquete

Coloca `astronex-py3-v2.1.tar.gz` donde quieras y extrae:

```bash
cd ~/Descargas    # o donde lo hayas dejado
tar xzf astronex-py3-v2.1.tar.gz
cd astronex
```

### A.3 — Compilar e iniciar

```bash
cd docker
docker compose up
```

La primera vez tomará **2-5 minutos** mientras descarga e instala
dependencias. Las siguientes ejecuciones arrancan en segundos.

Cuando veas:

```
astronex-py3  | 2026-XX-XX HH:MM:SS Europe/Madrid
astronex-py3  | XXX.XXXXXXX
```

…la aplicación está corriendo. Debería aparecer la ventana de Astro-Nex con
una carta del momento actual cargada.

### A.4 — Detener la aplicación

- **Cerrar la ventana**: cierra normalmente con la X de la ventana
- **Detener contenedor**: `Ctrl+C` en la terminal donde corre `docker compose up`
  - O desde otra terminal: `docker compose down`

### A.5 — Volver a iniciar

```bash
cd ~/Descargas/astronex/docker
docker compose up
```

### A.6 — Datos persistentes

Tus cartas, configuración y favoritos se guardan automáticamente en un
volumen de Docker (`astronex-py3-data`) que **persiste entre reinicios**.

Para hacer **backup**:

```bash
docker run --rm \
  -v astronex-py3-data:/data \
  -v $(pwd):/backup \
  ubuntu tar czf /backup/astronex-backup.tar.gz -C /data .
```

Para **restaurar** un backup:

```bash
docker run --rm \
  -v astronex-py3-data:/data \
  -v $(pwd):/backup \
  ubuntu tar xzf /backup/astronex-backup.tar.gz -C /data
```

---

## Ruta B — Instalación nativa (sin Docker)

Solo recomendada si por alguna razón no puedes usar Docker.

### B.1 — Dependencias del sistema

> **Importante:** instala **PyGObject y pycairo desde apt** (`python3-gi`,
> `python3-gi-cairo`, `python3-cairo`), NO con pip. Compilarlos con pip en
> Ubuntu 24.04/26.04 es frágil y suele fallar. La lista de abajo es válida en
> Ubuntu **22.04, 24.04 y 26.04**: los paquetes de runtime de GTK (libgtk-3,
> gdk-pixbuf, pango, cairo) los arrastra `gir1.2-gtk-3.0` automáticamente con el
> nombre correcto de cada versión, así que **no** hay que listarlos a mano (en
> 24.04+ algunos cambiaron de nombre, p. ej. `libgdk-pixbuf2.0-0` →
> `libgdk-pixbuf-2.0-0`, y listarlos provocaba el error "has no installation
> candidate" que abortaba toda la instalación).

```bash
# Ubuntu 22.04 / 24.04 / 26.04  ·  Debian 12+
sudo apt update
sudo apt install -y \
    python3 python3-pip python3-dev python3-venv \
    python3-gi python3-gi-cairo python3-cairo \
    gir1.2-gtk-3.0 \
    build-essential \
    fonts-dejavu-core fontconfig \
    xdg-utils evince eog
```

`build-essential` es necesario para compilar `pyswisseph` (extensión C) en el
paso B.2. `evince`/`eog` son visores de PDF/imagen (opcionales).

### B.2 — Dependencias Python

```bash
cd ~/Descargas/astronex   # donde hayas descomprimido

# Opción B.2.a — Con virtualenv (recomendado, no toca tu sistema)
# IMPORTANTE: --system-site-packages permite que el venv reutilice el PyGObject
# y pycairo que instalaste con apt (B.1) en vez de intentar recompilarlos.
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install --use-pep517 -r requirements.txt   # instala/compila solo pyswisseph, configobj, tzdata, Pillow

# Opción B.2.b — Instalación global (si tu distro lo permite)
pip3 install --break-system-packages --use-pep517 -r requirements.txt
```

### B.3 — Instalar la fuente Astro-Nex.ttf (CRÍTICO)

Sin esta fuente, los símbolos astrológicos (planetas, signos, aspectos)
NO se ven. Es obligatorio:

```bash
mkdir -p ~/.fonts
cp astronex/resources/Astro-Nex.ttf ~/.fonts/
fc-cache -f -v
```

Verifica que se instaló:

```bash
fc-list | grep -i astro
# Debe mostrar: /home/tu-usuario/.fonts/Astro-Nex.ttf: Astro-Nex:style=Regular
```

### B.4 — Ejecutar

```bash
# Si usaste virtualenv
source venv/bin/activate
python3 nex.py

# Si instalaste globalmente
python3 nex.py
```

### B.5 — Crear un acceso directo en el menú

Para tener Astro-Nex en el menú de aplicaciones de tu escritorio:

```bash
mkdir -p ~/.local/share/applications
cat > ~/.local/share/applications/astronex.desktop << EOF
[Desktop Entry]
Name=Astro-Nex
Comment=Cartas astrológicas método API
Exec=python3 $HOME/Descargas/astronex/nex.py
Path=$HOME/Descargas/astronex
Icon=$HOME/Descargas/astronex/astronex/resources/iconex-48.png
Type=Application
Categories=Science;Education;
EOF
chmod +x ~/.local/share/applications/astronex.desktop
```

Ajusta la ruta `$HOME/Descargas/astronex` si la descomprimiste en otro sitio.

---

## Primera vez que usas Astro-Nex

### Verificación inicial

Al arrancar verás:

1. **Splash screen** breve con el logo
2. **Ventana principal** con una carta del momento actual cargada
3. **Panel izquierdo** con tu lista de cartas y los selectores de tipo
4. **Panel derecho** con la rueda astrológica

Si la rueda muestra **letras o cuadrados en vez de símbolos astrológicos**,
la fuente Astro-Nex.ttf no se cargó. Repite el paso B.3 y reinicia la app.

### Datos de usuario

La aplicación crea automáticamente la carpeta `~/.Astronex/` con:

- `charts.db` — base de datos SQLite con tus cartas (incluye celebridades API
  de muestra)
- `cfg.ini` — configuración personalizable
- `mruch.pkl` — caché de personas recientes
- `coups.pkl` — caché de parejas

**No necesitas crear nada manualmente**, la app lo hace al primer arranque.

---

## Activar modo oscuro

Astro-Nex soporta tema oscuro. Para activarlo:

1. Abrir la app
2. Click en el icono de **herramientas** (en la barra superior) o pulsar
   `Ctrl+I` para abrir **Configuración**
3. Ir a la pestaña **Colores**
4. Marcar el checkbox **"Modo oscuro (requiere reiniciar)"** al final
5. Click en el botón **Guardar**
6. **Cerrar la app y volver a abrirla**
7. La app arranca en modo oscuro

Para volver a modo claro: misma ruta, desmarcar el checkbox, Guardar,
reiniciar.

La carta astrológica siempre se dibuja con fondo blanco (para legibilidad
de aspectos y export PNG/PDF). El modo oscuro afecta solo al panel
izquierdo, listas y diálogos.

---

## Atajos de teclado principales

| Atajo | Función |
|---|---|
| `F1` | Ayuda (muestra todos los atajos) |
| `F2` | Modificar carta actual |
| `F3` | Cargar momento actual al slot activo |
| `F4` | Abrir/cerrar calendario |
| `F5` | Volver a momento actual |
| `F6` | Mostrar Punto de Edad |
| `F11` | Pantalla completa |
| `Ctrl+B` | Explorador de cartas (4 pestañas: Explorador, Mezclador, Importación AAF, Parejas) |
| `Ctrl+C` | Calendario (igual que F4) |
| `Ctrl+D` | Diada (mini-carta auxiliar) |
| `Ctrl+E` | Nueva entrada (entrar carta nueva) |
| `Ctrl+G` | Exportar a PNG |
| `Ctrl+H` | Selector de aspectos |
| `Ctrl+I` | Configuración |
| `Ctrl+L` | Añadir/editar localidad |
| `Ctrl+P` | Exportar a PDF / Imprimir |
| `Ctrl+Q` | Salir |
| `Ctrl+R` | PE Puente |
| `Ctrl+W` | Ventana auxiliar |
| `Ctrl+X` | Alternar entre slots |
| `Ctrl+Y` | Selector de ciclos |
| `G` (con carta Radix) | Mostrar/ocultar tabla de grados de planetas |
| `Ctrl+Shift+J` | Activar modo Armónico 10 (oculto) |
| `Ctrl+Shift+U` | Volver a modo zodiacal normal (12) |

---

## Solución de problemas

### "permission denied" al ejecutar `docker compose`

Tu usuario no está en el grupo `docker`. Solución:

```bash
sudo usermod -aG docker $USER
# Cierra sesión y entra de nuevo (o reinicia)
```

### Instalación nativa: error "has no installation candidate" (Ubuntu 24.04 / 26.04)

Si al ejecutar el `apt install` del paso B.1 ves algo como
`E: Package 'libgdk-pixbuf2.0-0' has no installation candidate`, estás usando
una lista de paquetes antigua. En Ubuntu 24.04+ varios paquetes de GTK
cambiaron de nombre. **Usa la lista actualizada del paso B.1** (no incluye los
runtime de GTK a mano; los arrastra `gir1.2-gtk-3.0`). Verificado en Ubuntu
26.04 + Python 3.14.

### Instalación nativa: `pip` intenta compilar PyGObject/pycairo y falla

Síntoma: errores de compilación (meson/ninja/`girepository`) al hacer
`pip install -r requirements.txt`. Causa: el venv no ve el PyGObject de apt y
pip intenta construirlo. Solución: recrea el venv con
`python3 -m venv --system-site-packages venv` (paso B.2.a) tras instalar
`python3-gi python3-gi-cairo python3-cairo` con apt (B.1).

### Símbolos astrológicos se ven como cuadrados

La fuente `Astro-Nex.ttf` no se instaló. Para instalación nativa:

```bash
mkdir -p ~/.fonts
cp astronex/resources/Astro-Nex.ttf ~/.fonts/
fc-cache -f -v
```

Para Docker, la fuente está en `docker/fonts/Astro-Nex.ttf` y se monta
automáticamente. Si el contenedor no la encuentra, reconstruye:

```bash
cd astronex/docker
docker compose down
docker compose up --build
```

### El PDF se exporta pero no se abre solo

El visor por defecto (`evince`) viene preinstalado con Docker. Si usas
instalación nativa:

```bash
sudo apt install -y evince eog
```

O cambia el visor en Configuración → PNG (sección PDF) por uno instalado
en tu sistema.

### La ventana queda con el title bar blanco en modo oscuro (WSLg)

Limitación de WSL/WSLg: la barra de título la dibuja Windows, no GTK. En
Linux nativo con GNOME/KDE el título sí respeta el tema oscuro.

### Importación AAF con encoding raro

En el diálogo "Importación AAF", asegúrate de seleccionar el encoding
correcto del archivo `.aaf`:
- **Win-1252**: archivos de Mega-Star u otros programas Windows antiguos
- **utf-8**: archivos modernos

Marca primero "Simular" para previsualizar antes de importar de verdad.

### Quiero usar mis cartas viejas de la versión Py2

Copia el `charts.db` antiguo (de `~/.Astronex/` en tu sistema Py2 o de
`Documents and Settings\Usuario\.astronex` en Windows) al volumen Docker
o a `~/.Astronex/` si usas instalación nativa.

```bash
# Para Docker
docker run --rm -v astronex-py3-data:/data -v $(pwd):/source \
  ubuntu cp /source/charts.db /data/charts.db

# Para nativa
cp /ruta/al/charts.db.viejo ~/.Astronex/charts.db
```

El formato es compatible — Astro-Nex Py3 lee los mismos `charts.db` que Py2.

### Horario de verano (DST) — ahora automático

En esta versión (2.1), Astro-Nex calcula el horario de verano usando la
base de zonas horarias **IANA del sistema operativo** (vía `zoneinfo` de
Python 3). Esto resuelve casos como la **supresión del horario de verano en
México (octubre 2022)**: una carta mexicana posterior a esa fecha se calcula
correctamente en hora estándar (CST, UTC-6), **sin ajuste manual**.

**Cómo mantener las reglas actualizadas** (cuando un país cambie su DST):

- **Docker:** reconstruir la imagen toma la última base: `docker compose up --build`
- **Nativo / sistema:** `sudo apt upgrade tzdata` (Ubuntu/Debian) actualiza la
  base IANA del sistema.
- **Alternativa pip:** `pip install -U tzdata`

No hace falta tocar código ni reinstalar la aplicación; basta actualizar la
base de zonas y reiniciar Astro-Nex.

---

## Soporte y contacto

- **Migración Python 3 (José Alejandro Pech)**: para problemas técnicos de
  instalación o errores nuevos introducidos en la migración
- **Documentación y soporte de uso (Joan Solé)**: joansole@api-ediciones.com
- **Autor original**: José Antonio Rodríguez (✝ 2022)
- **Web**: https://www.astro-nex.net

---

## Resumen ejecutivo (TLDR)

```bash
# Linux con Docker
sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER
# reinicia sesion
tar xzf astronex-py3-v2.1.tar.gz
cd astronex/docker
docker compose up
```

Eso es todo.
