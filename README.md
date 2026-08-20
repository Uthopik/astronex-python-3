# Astro-Nex (Python 3 / GTK3)

Astronex is a program for calculating and drawing astrological charts according to the API Method. Used in Huber method. Python 3 version.

In the ‘Releases’ section, you’ll find four files:

## Windows

- Astro-Nex-Dark-v2.1-setup.exe (Windows installer)
- Astro-Nex-Portable.exe (Portable version)

## Linux

- Astro-Nex-Dark-v2.1.AppImage
- astro-nex-dark-v2.1.deb

https://github.com/Uthopik/astronex-python-3/releases/tag/v2.1

## Instalación

- On Windows, simply double-click the file and, if prompted for permission, grant it.

- On Linux, right-click the AppImage file and grant permission via the ‘Permissions’ menu. Alternatively, in the terminal, grant permission using:
chmod +x ./Astro-Nex-Dark-v2.1.AppImage

- On Debian-based Linux distributions (Ubuntu, Linux Mint, etc.), you can install it using a .deb file. Open the terminal where the file is located and run this command:
sudo apt install ./astro-nex-dark-v2.1.deb
Enter your password and press Enter.


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
