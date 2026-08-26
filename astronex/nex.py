#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys
import os
import atexit
import gi

gi.require_version('PangoFT2', '1.0')
from gi.repository import PangoFT2

def register_astro_font(appath):
    """Registra dinamicamente Astro-Nex.ttf en el mapa de fuentes de Pango."""
    # Base dir para PyInstaller empaquetado
    base_dir = getattr(sys, '_MEIPASS', appath)

    possible_paths = [
        os.path.join(base_dir, "astronex", "resources", "Astro-Nex.ttf"),
        os.path.join(base_dir, "resources", "Astro-Nex.ttf"),
        os.path.join(appath, "astronex", "resources", "Astro-Nex.ttf"),
        os.path.join(appath, "resources", "Astro-Nex.ttf"),
        os.path.expanduser("~/Library/Fonts/Astro-Nex.ttf"),
        os.path.expanduser("~/.fonts/Astro-Nex.ttf")
    ]
    
    font_path = None
    for p in possible_paths:
        if os.path.exists(p):
            font_path = p
            break

    if font_path:
        fontmap = PangoFT2.FontMap.get_default()
        fontmap.add_font_file(font_path)
        print(f"[OK] Fuente Astro-Nex cargada dinamicamente desde: {font_path}")
    else:
        print("[AVISO] No se encontro el archivo Astro-Nex.ttf para registrar en Pango")

def _setup_and_update_tzdata():
    """Configura tzdata de PyPI como fuente de zonas horarias y lo actualiza
    en segundo plano si hay conexion a internet.

    Al apuntar TZDIR al paquete tzdata de PyPI (en lugar de /usr/share/zoneinfo
    del SO), la actualizacion via 'pip install -U tzdata' tiene efecto sin
    necesidad de sudo ni reconstruir el contenedor Docker.
    Si no hay internet, falla silenciosamente y usa los datos actuales.
    Los datos nuevos se aplican en el proximo arranque de la app.
    """
    # 1. Apuntar TZDIR al tzdata de PyPI (system o --user) para que zoneinfo
    #    lo use en lugar de /usr/share/zoneinfo del SO.
    def _find_tzdata_path():
        try:
            from importlib.resources import files as _files
            p = str(_files('tzdata').joinpath('zoneinfo'))
            if os.path.isdir(p):
                return p
        except Exception:
            pass
        # Buscar tambien en ~/.local (instalacion --user del usuario actual)
        import site
        for sp in site.getusersitepackages() if isinstance(
                site.getusersitepackages(), list) else [site.getusersitepackages()]:
            p = os.path.join(sp, 'tzdata', 'zoneinfo')
            if os.path.isdir(p):
                return p
        return None

    _tz_path = _find_tzdata_path()
    if _tz_path:
        os.environ['TZDIR'] = _tz_path

    # 2. Actualizar tzdata en segundo plano si hay internet.
    #    --user: instala en ~/.local sin necesitar permisos de root.
    #    Tras actualizar, si la version nueva esta en ~/.local, apunta TZDIR ahi.
    import threading

    def _update_tzdata():
        try:
            import subprocess
            r = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', '-q',
                 '--upgrade', '--user', '--break-system-packages', 'tzdata'],
                timeout=20,
                capture_output=True,
            )
            if r.returncode == 0:
                # Redirigir TZDIR a la version recien instalada en ~/.local
                new_path = _find_tzdata_path()
                if new_path:
                    os.environ['TZDIR'] = new_path
        except Exception:
            pass  # sin internet o pip no disponible: no pasa nada

    t = threading.Thread(target=_update_tzdata, daemon=True)
    t.start()


_setup_and_update_tzdata()


import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, GdkPixbuf, GLib

if os.environ.get('ASTRONEX_DIAG'):
    # DIAGNOSTICO TEMPORAL (activar con ASTRONEX_DIAG=1): imprime la pila de
    # Python en el momento exacto de cada aviso critico de Gtk/GObject, sin
    # detener la app, para ubicar la causa del cuadro negro (Ctrl+L -> Nueva
    # Entrada). Quitar este bloque una vez encontrada la causa raiz.
    import sys
    import traceback

    def _diag_log_handler(domain, level, message, *a):
        sys.stderr.write("\n=== DIAG CRITICAL [%s]: %s\n" % (domain, message))
        traceback.print_stack(file=sys.stderr)
        sys.stderr.write("=== fin pila DIAG ===\n\n")

    GLib.log_set_handler("Gtk", GLib.LogLevelFlags.LEVEL_CRITICAL, _diag_log_handler)
    GLib.log_set_handler("GLib-GObject", GLib.LogLevelFlags.LEVEL_CRITICAL, _diag_log_handler)

import gettext

from astronex import countries
from astronex.config import read_config
from astronex.extensions.path import path

# --- RESOLUCIÓN DINÁMICA DE RUTAS DE TRADUCCIÓN (gettext) ---
if getattr(sys, 'frozen', False):
    # Si la app está empaquetada con PyInstaller en macOS/Linux
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    locale_dir = os.path.join(base_dir, 'astronex', 'locale')
    if not os.path.exists(locale_dir):
        locale_dir = os.path.join(base_dir, 'locale')
else:
    # Si se ejecuta desde el código fuente
    base_dir = os.path.dirname(os.path.abspath(__file__))
    locale_dir = os.path.join(base_dir, 'astronex', 'locale')
    if not os.path.exists(locale_dir):
        locale_dir = os.path.join(base_dir, 'locale')

lang_es = gettext.translation('astronex', locale_dir, languages=['es'], fallback=True)
lang_en = gettext.translation('astronex', locale_dir, languages=['en'], fallback=True)
lang_ca = gettext.translation('astronex', locale_dir, languages=['ca'], fallback=True)
lang_de = gettext.translation('astronex', locale_dir, languages=['de'], fallback=True)
langs = {'en': lang_en, 'es': lang_es, 'ca': lang_ca, 'de': lang_de}

version = "2.1"


def die(message):
    """Die in a command line way."""
    print(message, file=sys.stderr)
    sys.exit(1)


home_dir = '.Astronex'
config_file = 'cfg.ini'
default_db = 'charts.db'
ephe_path = 'ephe'
ephe_flag = 4

def main(appath, console=False):
    # 1. Registrar la fuente Astro-Nex en Pango antes de instanciar GTK
    register_astro_font(appath)

    # 2. Continuar con la carga normal
    check_home_dir(appath)
    _early_apply_darkmode(home_dir)
    app = application(appath)
    app.run()

def check_home_dir(appath):
    """Set home dir, copying needed files"""
    global home_dir, ephe_flag
    default_home = path.joinpath(path.expanduser(path('~')), home_dir)

    if not path.exists(default_home):
        path.mkdir(default_home)
    ephepath = path.joinpath(default_home, ephe_path)
    if not path.exists(ephepath):
        path.mkdir(ephepath)
        readme_src = path.joinpath(appath, "astronex/resources/README")
        if not path.exists(readme_src):
            readme_src = path.joinpath(appath, "resources/README")
        if path.exists(readme_src):
            path.copy(readme_src, ephepath)
            
    if ephepath.glob("*.se1"):
        ephe_flag = 2
        
    if not path.exists(path.joinpath(default_home, default_db)):
        db_src = path.joinpath(appath, "astronex/resources/charts.db")
        if not path.exists(db_src):
            db_src = path.joinpath(appath, "resources/charts.db")
        if path.exists(db_src):
            path.copy(db_src, default_home)

    cfg_src = path.joinpath(appath, "astronex/resources/cfg.ini")
    if not path.exists(cfg_src):
        cfg_src = path.joinpath(appath, "resources/cfg.ini")
    cfg_dst = path.joinpath(default_home, config_file)
    if not path.exists(cfg_dst) and path.exists(cfg_src):
        path.copy(cfg_src, default_home)

    home_dir = default_home


def init_config(homedir, opts, state):
    ephepath = path.joinpath(homedir, opts.ephepath)
    from pysw import setpath
    setpath(str(ephepath))

    state.country = opts.country
    state.usa = {'false': False, 'true': True}[opts.usa]
    state.database = opts.database
    state.setloc(opts.locality, opts.region)
    state.init_nowchart()
    state.curr_chart = state.now
    state.epheflag = ephe_flag
    opts.epheflag = ephe_flag

    if opts.favourites:
        try:
            tbl = opts.favourites
            nfav = int(opts.nfav)
            favs = state.datab.get_favlist(tbl, nfav, state.newchart())
            state.fav = favs
        except Exception:
            pass

    from astronex.chart import orbs as ch_orbs
    orbs = [opts.lum, opts.normal, opts.short, opts.far, opts.useless]
    for l in orbs:
        state.orbs.append(list(map(float, l)))
        ch_orbs.append(list(map(float, l)))
    peorbs = [opts.pelum, opts.penormal, opts.peshort, opts.pefar, opts.peuseless]
    for l in peorbs:
        state.peorbs.append(list(map(float, l)))
    for l in opts.transits:
        state.transits.append(float(l))
    opts.discard = [int(x) for x in opts.discard]


class Splash(Gtk.Window):
    def __init__(self, appath):
        Gtk.Window.__init__(self, type=Gtk.WindowType.TOPLEVEL)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_default_size(400, 250)
        self.set_position(Gtk.WindowPosition.CENTER)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        img = Gtk.Image()
        
        # Buscar en astronex/resources/splash.png o en resources/splash.png
        splashimg = path.joinpath(appath, "astronex/resources/splash.png")
        if not path.exists(splashimg):
            splashimg = path.joinpath(appath, "resources/splash.png")

        img.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file(str(splashimg)))
        vbox.pack_start(img, True, True, 0)
        self.add(vbox)


class application(object):
    """The Nex Application."""

    def __init__(self, appath):
        self.home_dir = home_dir
        self.config_file = config_file
        self.default_db = default_db
        self.appath = appath
        self.version = version
        self.langs = langs

    def run(self):
        """Start Nex"""
        splash = Splash(self.appath)
        splash.show_all()
        GLib.timeout_add(1000, splash.hide)
        GLib.idle_add(self.setup_app)
        Gtk.main()

    def setup_app(self):
        opts = read_config(self.home_dir)
        opts.home_dir = self.home_dir
        langs[opts.lang].install()
        countries.install(opts.lang)
        self.lang = opts.lang
        # Aplicar modo oscuro si esta activado en cfg.ini
        dark = str(getattr(opts, 'darkmode', 'false')).lower() in ('true', '1', 'yes')
        if dark:
            settings = Gtk.Settings.get_default()
            if settings:
                settings.set_property('gtk-application-prefer-dark-theme', True)
        from astronex.state import Current
        from astronex.boss import Manager
        state = Current(self)
        atexit.register(state.save_pool, self)
        init_config(self.home_dir, opts, state)
        boss = Manager(self, opts, state)
        from astronex.gui.winnex import WinNex
        mainwin = WinNex(boss)
        boss.set_mainwin(mainwin)

    def stop(self):
        """Stop Nex."""
        Gtk.main_quit()


def _early_apply_darkmode(home):
    """Lee cfg.ini y aplica GTK_THEME ANTES de crear cualquier widget GTK."""
    from configobj import ConfigObj
    cfgfile = path.joinpath(home, 'cfg.ini')
    if not path.exists(cfgfile):
        return
    try:
        conf = ConfigObj(str(cfgfile), encoding='utf-8')
    except Exception:
        return
    val = conf.get('DEFAULT', {}).get('darkmode', 'false')
    if str(val).lower() in ('true', '1', 'yes'):
        os.environ['GTK_THEME'] = 'Adwaita:dark'
