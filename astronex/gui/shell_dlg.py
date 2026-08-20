"""Stub del dialogo de shell IPython — DESACTIVADO en la migracion a Python 3.

Cliente confirmo que la consola IPython no es necesaria (solo usa la GUI).
Esta clase muestra un dialogo informativo en lugar de la shell embebida.
Ver tests/divergences.md para justificacion.
"""
from gi.repository import Gtk


class ShellDialog(Gtk.MessageDialog):
    def __init__(self, manager):
        super().__init__(
            transient_for=getattr(manager, 'mainwin', None),
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.CLOSE,
            text="Consola IPython no disponible",
        )
        self.format_secondary_text(
            "La consola IPython embebida fue desactivada en la migracion a Python 3.\n"
            "Si necesita inspeccionar el estado del programa, use un debugger externo."
        )
        # Ocultar (no destruir) al cerrar: destruir esta toplevel en GTK3/WSLg
        # provoca un segfault. Es un stub que se reabre raramente (Ctrl+K).
        self.connect("response", lambda d, r: d.hide())
        # Ocultar en 'response' NO evita el destroy con ESC/la X: lo hace
        # gtk_main_do_event() cuando la emision de 'delete-event' devuelve
        # FALSE. connect_after conserva el comportamiento (el handler de clase
        # emite 'response') y devuelve True para que no se destruya.
        # Ver la nota larga en entry_dlg.py.
        self.connect_after("delete-event", lambda w, e: True)
        self.show()
