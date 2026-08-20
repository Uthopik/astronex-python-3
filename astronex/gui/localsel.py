# -*- coding: utf-8 -*-
from gi.repository import Gtk

from astronex.gui.localwidget import LocWidget


class LocSelector(Gtk.Dialog):
    '''New chart inputs dialog'''

    def __init__(self, parent, calc=False):
        self.boss = parent.boss
        # Sin destroy_with_parent: el dialogo se oculta y se reutiliza (winnex.locsel),
        # nunca se destruye durante la sesion (evita el segfault de GTK3/WSLg).
        Gtk.Dialog.__init__(self,
                            title=_("Localidad"),
                            transient_for=parent)
        self.connect('configure-event', self.on_configure_event)

        self.set_size_request(400, 500)
        content = self.get_content_area()
        content.set_border_width(3)

        loc = self.create_locwidget()
        content.pack_start(loc, True, True, 0)

        self.connect("response", self.quit_response, parent)
        # Mismo caso que EntryDlg: ocultar desde 'response' NO evita el destroy.
        # gtk_main_do_event() destruye la ventana si la emision de
        # 'delete-event' devuelve FALSE, y el handler de clase de GtkDialog
        # devuelve FALSE tras emitir 'response'. Con connect_after el handler de
        # clase sigue corriendo (quit_response se ejecuta igual) pero la
        # emision acaba en True y la instancia retenida en winnex.locsel
        # sobrevive; si no, al reabrirla con Ctrl+N saldria un cuadro negro.
        self.connect_after('delete-event', self.on_delete_keep_alive)
        self.show_all()

        wpos = self.get_position()
        self.pos_x = wpos[0]
        self.pos_y = wpos[1]

    def on_delete_keep_alive(self, widget, event):
        return True

    def on_configure_event(self, widget, event):
        self.pos_x = event.x
        self.pos_y = event.y

    def quit_response(self, dialog, rid, parent):
        # No destruir el dialogo: destruirlo con ESC/X en GTK3 sobre WSLg
        # provocaba un segfault que mataba toda la app. En su lugar lo
        # OCULTAMOS y conservamos la instancia en parent.locsel para
        # reutilizarla (se vuelve a mostrar con Ctrl+N). Mantenemos el
        # flag locselflag = False para que localwidget.py lo vea al cerrar.
        self.boss.mainwin.locselflag = False
        dialog.hide()

    def dlg_response(self, but, dialog, rid, parent):
        # Mismo criterio que quit_response: ocultar en vez de destruir para
        # evitar el segfault de finalizacion en WSLg/GTK3 y reutilizar la
        # instancia retenida en parent.locsel.
        self.boss.mainwin.locselflag = False
        dialog.hide()

    def create_locwidget(self):
        loc = LocWidget()
        frame = Gtk.Frame()
        frame.set_border_width(3)
        frame.add(loc)
        return frame
