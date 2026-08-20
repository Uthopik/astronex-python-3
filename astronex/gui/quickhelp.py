# -*- coding: utf-8 -*-
"""Ventana de ayuda — atajos de teclado y de raton.

Estructura propuesta por el cliente Elias (mayo 2026):
- Anade tecla G para ventana de grados persistente (Feature B).
- Documenta Ctrl-Shift-J/U para Armonico 10 (Feature C).
"""
from gi.repository import Gtk, Gdk, Pango


_KEYBOARD = [
    ("F1",              _("Esta ayuda")),
    ("G",               _("Ventana de grados")),
    ("Ctrl-Q",          _("Salir")),
    ("F11 (Esc)",       _("Pantalla completa")),
    ("Ctrl-G",          _("Exportar a imagen")),
    ("Ctrl-P",          _("Exportar a PDF / Imprimir")),
    ("Ctrl-E",          _("Cuadro de entradas")),
    ("Ctrl-S",          _("Cuadro de configuracion")),
    ("Ctrl-F",          _("Buscar tecleando en listas")),
    ("Esc",             _("Cerrar ventana/dialogo")),
    ("Ctrl-X",          _("Alternar casillas")),
    ("Ctrl-C, F5",      _("Calendario")),
    ("Ctrl-A, F6",      _("PE")),
    ("Ctrl-W",          _("Ventana auxiliar")),
    ("Ctrl-H",          _("Selector de aspectos")),
    ("Ctrl-D",          _("Diagramas")),
    ("Ctrl-Y",          _("Ciclos")),
    ("Ctrl-R",          _("PE Puente")),
    ("Ctrl-L",          _("Anadir localidad")),
    ("Ctrl-B",          _("Navegador rapido cartas")),
    ("Cursores",        _("Moverse en listas")),
    ("0-9 Tecl. num.",  _("Seleccionar lista")),
    ("+/- Tecl. num.",  _("Rotar tambor de personas")),
    ("Ctrl-Shift-J",    _("Armonico 10")),
    ("Ctrl-Shift-U",    _("Quitar Armonico 10")),
    ("+/-",             _("Rotar casas (biografia)")),
]

_MOUSE = [
    # (Accion, Accion2, Donde)
    ("Clic",            _("Situar PE"),         _("PE, biografia")),
    ("",                _("Ojo"),                _("Personas recientes")),
    ("Clic derecho",    _("Menu secundario"),    _("Area de dibujo")),
    ("",                "",                       _("Ventana auxiliar")),
    ("",                "",                       _("Casillas")),
    ("",                "",                       _("Listas de cartas")),
    ("Doble clic",      _("Fecha = Hoy"),        _("PE, biografia")),
    ("",                "",                       _("Carta reloj, transitos")),
    ("",                "",                       _("Selector de casas")),
    ("Arrastrar",       _("Principio de lista"), _("Ventana auxiliar")),
    ("",                _("Guia de grados"),     _("Area de dibujo")),
    ("",                _("Mover PE"),           _("Biografia")),
    ("",                _("Arrastrar carta"),    _("Zoom")),
    ("",                _("Mover registros"),    _("Entre tablas")),
    ("Rueda",           _("Rotar lista"),        _("Areas de dibujo")),
    ("",                _("Rotar tambor pers."), _("Casillas")),
    ("Boton rueda",     _("Principio lista"),    _("Lista principal")),
    ("",                _("Ventana de grados"),  "Radix"),
    ("",                _("Alternar posicion"),  _("Listas dobles/triples")),
    ("",                _("Alternar con guia"),  "Zoom"),
    ("",                _("Mover PE 180°"),  "PE"),
    ("+ Ctrl",          _("mover PE +30°"), ""),
    ("+ Ctrl-May",      _("Mover PE -30°"), ""),
]


def _make_section(title, columns, rows):
    """Construye un Frame con un Grid de filas tipo (col1, col2, col3?)."""
    frame = Gtk.Frame()
    frame.set_label_align(0.5, 0.5)
    # Titulo en negrita via markup (en vez de Pango.AttrList/attr_weight_new,
    # que era una via de finalizacion problematica al destruir la ventana).
    label = Gtk.Label()
    label.set_markup("<b>%s</b>" % title)
    frame.set_label_widget(label)

    grid = Gtk.Grid()
    grid.set_column_spacing(12)
    grid.set_row_spacing(2)
    grid.set_margin_start(10)
    grid.set_margin_end(10)
    grid.set_margin_top(6)
    grid.set_margin_bottom(6)

    # Header
    for i, col in enumerate(columns):
        hdr = Gtk.Label()
        hdr.set_markup("<b>%s</b>" % col)
        hdr.set_xalign(0.0)
        grid.attach(hdr, i, 0, 1, 1)

    # Rows
    for row_ix, row in enumerate(rows, start=1):
        for col_ix, cell in enumerate(row):
            lbl = Gtk.Label(label=cell)
            lbl.set_xalign(0.0)
            grid.attach(lbl, col_ix, row_ix, 1, 1)

    frame.add(grid)
    return frame


class HelpWindow(Gtk.Window):
    """Ventana modal de ayuda — atajos teclado + raton."""

    def __init__(self, parent):
        Gtk.Window.__init__(self)
        self.set_title(_("Ayuda"))
        self.set_transient_for(parent)
        self.set_modal(False)
        self.set_default_size(740, 580)

        # ESC o la X = OCULTAR la ventana (no destruirla) y reutilizarla luego.
        # Destruir esta ventana con ESC en GTK3 provocaba un segfault que mataba
        # toda la app; al no destruirla NUNCA durante la sesion se evita por
        # completo el camino de finalizacion que crasheaba. La ventana se crea
        # una vez (winnex.help_win) y se vuelve a mostrar con F1.
        self.connect('key-press-event', self.on_key_press)
        self.connect('delete-event', self.on_delete)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        hbox.set_border_width(8)

        # Columna izquierda: teclado
        kb_rows = [(k, ":  " + v) for k, v in _KEYBOARD]
        kb_frame = _make_section(_("Teclado"), [_("Tecla"), _("Accion")], kb_rows)
        sw_kb = Gtk.ScrolledWindow()
        sw_kb.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw_kb.add(kb_frame)
        hbox.pack_start(sw_kb, True, True, 0)

        # Columna derecha: raton
        mouse_frame = _make_section(_("Raton"),
                                    [_("Boton"), _("Accion"), _("Donde")],
                                    _MOUSE)
        sw_m = Gtk.ScrolledWindow()
        sw_m.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw_m.add(mouse_frame)
        hbox.pack_start(sw_m, True, True, 0)

        self.add(hbox)
        self.show_all()

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.hide()
            return True
        return False

    def on_delete(self, widget, event):
        # No destruir: ocultar (return True evita el destroy por defecto)
        self.hide()
        return True
