# -*- coding: utf-8 -*-
from gi.repository import Gtk, Gdk, Pango

from astronex.drawing.dispatcher import DrawMixin


class PlanSelector(Gtk.Dialog):
    '''Planet selector'''

    def __init__(self, parent):
        self.parnt = parent
        self.notwanted = set()
        self.plet = ['d', 'f', 'h', 'j', 'k', 'l', 'g', 'z', 'x', 'c', 'v']

        Gtk.Dialog.__init__(self,
                            title=_("Selector de aspectos"),
                            transient_for=parent,
                            destroy_with_parent=True)
        self.add_button(_("_Cerrar"), Gtk.ResponseType.NONE)

        content = self.get_content_area()
        content.set_border_width(3)
        frame = Gtk.Frame(label=_("Ocultar"))
        frame.set_border_width(3)

        frame.add(self.create_buttonlist())
        content.pack_start(frame, False, False, 0)

        self.connect("response", self.dlg_response)
        self.connect('key-press-event', self.on_key_press_event, parent)

        # Evitar que GTK3 re-centre el dialogo sobre el padre (la carta): asi se
        # respeta el move() posterior de make_plsel a la esquina (Errores2 #5).
        self.set_position(Gtk.WindowPosition.NONE)
        self.show_all()
        self.parnt.da.redraw()

    def create_buttonlist(self):
        font = Pango.FontDescription.from_string("Astro-Nex")
        vbuttonbox = Gtk.ButtonBox(orientation=Gtk.Orientation.VERTICAL)
        for let in self.plet:
            but = Gtk.ToggleButton(label=let)
            but.get_child().override_font(font)
            but.set_mode(True)
            but.connect("toggled", self.on_but_toggled)
            vbuttonbox.pack_start(but, False, False, 0)
        return vbuttonbox

    def on_but_toggled(self, but):
        let = but.get_label()
        if but.get_active():
            self.notwanted.add(self.plet.index(let))
        else:
            self.notwanted.discard(self.plet.index(let))
        DrawMixin.notwanted = list(self.notwanted)
        self.parnt.da.redraw()
        self.parnt.da.redraw_auxwins()

    def dlg_response(self, dialog, rid):
        self.parnt.boss.mpanel.toolbar.get_nth_item(3).set_active(False)

    def on_key_press_event(self, window, event, parent):
        if event.keyval == Gdk.KEY_Escape:
            parent.boss.mpanel.toolbar.get_nth_item(3).set_active(False)
        return True

    def exit(self):
        DrawMixin.notwanted = []
        self.parnt.da.redraw()
        self.parnt.da.plselector = None
        self.destroy()
