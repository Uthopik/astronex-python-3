# Astro-Nex (Python 3 / GTK3)

Astro-Nex es un programa de cálculo y dibujo de cartas astrológicas según el
**método API** (Astrologisch-Psychologisches Institut) de Bruno y Louise Huber.

Esta versión está migrada a **Python 3.12** con **GTK3** (vía PyGObject) y
**Swiss Ephemeris** (vía pyswisseph). Reemplaza la versión original de
Python 2.7 + PyGTK 2 escrita por José Antonio Rodríguez (✝ 2022).

## Características

- Cálculo de carta natal (Radix), Casas, Nodal, Causal, Dharma, Local, Perfil,
  Integración, Clic individual, Radix-Causal, Radix-Dharma
- Tránsitos, Progresión Secundaria, Revolución Solar
- Biografía sincronizada (PE — Punto de Edad)
- Diagramas de frustración/estrés, Planetograma, Paarwabe (panal de pareja)
- Comparación doble y triple (master/clic)
- Exportación a PNG y PDF
- Importación AAF para intercambiar cartas
- Modo oscuro (auto-detecta tema del sistema)
- Atajos: F2 modificar carta, F3 click clock, F4 calendario, F5 ahora,
  F6 Punto Edad, Ctrl+Y ciclos, Ctrl+B explorador, Ctrl+Shift+J armónico 10,
  tecla G tabla de grados persistente, y más.

## Requisitos

- **Linux** (probado en Ubuntu 24.04, Debian 12)
- **Python 3.10+** (recomendado 3.12)
- **GTK 3.24+**
- **Cairo / Pango / GLib** (sistema)
- Conexión a internet solo para instalación inicial

## Instalación

Ver [INSTALL.md](INSTALL.md) para instrucciones detalladas.

Resumen:

```bash
# 1. Paquetes del sistema (Ubuntu/Debian)
sudo apt install python3 python3-pip python3-gi python3-gi-cairo \
    gir1.2-gtk-3.0 libgtk-3-0 libcairo2 libpango-1.0-0 evince eog

# 2. Instalar fuente astrológica (CRÍTICO)
mkdir -p ~/.fonts
cp astronex/resources/Astro-Nex.ttf ~/.fonts/
fc-cache -f -v

# 3. Dependencias Python
pip3 install --break-system-packages --use-pep517 -r requirements.txt

# 4. Ejecutar
python3 nex.py
```

## Alternativa: Docker

Si prefieres no instalar dependencias en tu sistema:

```bash
cd docker-py3
docker compose up
```

Requiere WSLg en Windows o un X server en Linux nativo.

## Estructura

- `nex.py` — entry point principal
- `pysw.py` — wrapper de Swiss Ephemeris (reemplaza `_pysw.so` antiguo)
- `astronex/` — código principal
  - `gui/` — interfaz GTK3
  - `drawing/` — dibujo Cairo de cartas
  - `surfaces/` — superficies de export (PNG, PDF, etc.)
  - `db/local.db` — base de datos de localidades mundiales
  - `resources/` — fuente, iconos, charts.db inicial
  - `locale/` — traducciones (es/en/ca/de)
- `docker-py3/` — Dockerfile + docker-compose.yml para correr en contenedor

## Datos de usuario

La aplicación crea y mantiene los datos en `~/.Astronex/`:

- `charts.db` — base de datos SQLite con tus cartas
- `cfg.ini` — configuración personalizada (colores, fuentes, locale)
- `mruch.pkl` — pool de cartas recientes
- `coups.pkl` — pool de parejas

## Licencia

GPL. Ver el archivo `astronex/resources/COPYING`.

## Autores

- **José Antonio Rodríguez** — autor original (Py2 + PyGTK2)
- **José Alejandro Pech Interian** — migración Py3 + GTK3 (2026)
- **Cliente**: Elías José Sagardia
- **Documentación**: Joan Solé (api-ediciones)

https://www.astro-nex.net
