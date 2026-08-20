# -*- coding: utf-8 -*-
"""Editor visual de cfg.ini (Ctrl+I). Migrado de PyGTK2 a GTK3."""
from io import StringIO

from gi.repository import Gtk

from configobj import ConfigObj, ConfigObjError

from astronex.extensions.path import path
from astronex.config import reload_config


class IniEditor(Gtk.Dialog):
    def __init__(self, parent):
        self.boss = parent.boss
        Gtk.Dialog.__init__(self, title=_("Editor cfg.ini"),
                            transient_for=parent)
        # No destruir el dialogo al cerrar (ESC/Cerrar): se OCULTA y se reutiliza
        # (lo retiene winnex.inieditor). Destruirlo en WSLg/GTK3 provoca segfault.
        # Por eso tampoco se usa destroy_with_parent.
        self.add_button(_("Cerrar"), Gtk.ResponseType.NONE)
        self.add_button(_("Guardar"), Gtk.ResponseType.OK)
        self.set_default_size(480, 520)
        self.set_resizable(True)

        box = self.get_content_area()
        box.set_border_width(6)
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        textview = Gtk.TextView()
        textview.set_monospace(True)
        self.textbuffer = textview.get_buffer()
        sw.add(textview)
        box.pack_start(sw, True, True, 0)

        self.cfgfile = path.joinpath(self.boss.opts.home_dir, 'cfg.ini')
        self.reload_text()

        self.connect("response", self.dlg_response)
        self.connect("delete-event", self.on_delete)
        self.show_all()

    def reload_text(self):
        # Recarga el contenido de cfg.ini desde disco (llamado al crear y al
        # reabrir el editor reutilizado, para mostrar siempre lo guardado).
        try:
            with open(self.cfgfile, "r", encoding='utf-8') as infile:
                self.textbuffer.set_text(infile.read())
        except OSError:
            self.textbuffer.set_text("")

    def on_delete(self, dialog, event):
        # La X cierra ocultando, no destruyendo (return True evita el destroy).
        self.hide()
        return True

    def dlg_response(self, dialog, rid):
        if rid == Gtk.ResponseType.OK:
            start = self.textbuffer.get_start_iter()
            end = self.textbuffer.get_end_iter()
            text = self.textbuffer.get_text(start, end, True)
            infile = StringIO(text)
            try:
                conf = ConfigObj(infile, encoding='utf-8')
                conf.filename = self.cfgfile
                conf.write()
                reload_config(conf, self.boss)
            except ConfigObjError as e:
                errdialog = Gtk.MessageDialog(
                    transient_for=self, modal=True,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK, text=str(e))
                errdialog.run()
                errdialog.hide()  # no destruir (camino de segfault en WSLg)
                return  # no cerrar: dejar que el usuario corrija
            # refrescar la carta para que apliquen colores/orbes editados
            try:
                self.boss.redraw()
            except Exception:
                pass
        # Ocultar en vez de destruir: la instancia se reutiliza (winnex.inieditor)
        # y nunca se destruye durante la sesion -> se evita el segfault de GTK3.
        dialog.hide()
