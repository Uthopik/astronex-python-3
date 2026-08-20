# -*- coding: utf-8 -*-
from gi.repository import Gtk, Gdk


class CycleSelector(Gtk.Dialog):
    '''Cycle selector'''

    def __init__(self, parent):
        self.parnt = parent

        Gtk.Dialog.__init__(self,
                            title=_("Selector de ciclos PE"),
                            transient_for=parent,
                            destroy_with_parent=True)
        self.add_button(_("_Cerrar"), Gtk.ResponseType.NONE)

        content = self.get_content_area()
        content.set_border_width(3)
        frame = Gtk.Frame(label=_("Ciclos PE"))
        frame.set_border_width(3)

        self.person2 = False
        cycles = self.parnt.boss.state.get_cycles()

        adj = Gtk.Adjustment(value=cycles + 1, lower=-10, upper=30,
                             step_increment=1, page_increment=1, page_size=0)
        spin = Gtk.SpinButton()
        spin.set_adjustment(adj)
        spin.set_wrap(False)
        spin.set_alignment(1.0)
        adj.connect("value-changed", self.on_spin_changed, spin)
        frame.add(spin)
        content.pack_start(frame, False, False, 0)
        self.adj = adj

        self.connect("response", self.dlg_response)
        self.connect('key-press-event', self.on_key_press_event, parent)
        # El boton X (delete-event) NO debe destruir el dialogo: en WSLg/GTK3
        # destruirlo provoca un segfault que mata la app. Se enruta por el
        # mismo contrato del toggle (poner el boton de toolbar inactivo) y se
        # bloquea el destroy por defecto devolviendo True.
        self.connect('delete-event', self.on_delete, parent)
        self.set_size_request(120, -1)
        self.show_all()

    def on_spin_changed(self, widget, spin):
        # La instancia ya no se destruye al cerrar (se oculta y se retiene en
        # da.cycleselector para reutilizarla, evitando el segfault de GTK3 en
        # WSLg). Como queda 'truthy' aunque oculta, otros sitios (actualize_pool,
        # doble-clic, set_date) siguen llamando a .adj.set_value(...), lo que
        # dispararia este handler y cambiaria la fecha (update_cycles) con el
        # selector CERRADO. Para conservar el comportamiento original (cuando
        # cerrado equivalia a None y no tocaba la fecha) ignoramos los cambios
        # mientras el dialogo no este visible.
        if not self.get_visible():
            return
        delta = spin.get_value_as_int() - 1
        prev_cyc = self.parnt.boss.state.get_cycles(self.person2)
        self.parnt.da.panel.update_cycles(delta - prev_cyc)

    def refresh_spin(self):
        cycles = self.parnt.boss.state.get_cycles()
        self.set_value(cycles + 1)

    def set_value(self, value):
        self.adj.set_value(value)

    def dlg_response(self, dialog, rid):
        self.parnt.boss.mpanel.toolbar.get_nth_item(4).set_active(False)

    def on_key_press_event(self, window, event, parent):
        keyval = event.keyval
        state = event.state & Gtk.accelerator_get_default_mod_mask()
        if keyval == Gdk.KEY_Escape or state == Gdk.ModifierType.MOD1_MASK:
            parent.boss.mpanel.toolbar.get_nth_item(4).set_active(False)
        return True

    def on_delete(self, window, event, parent):
        # El boton X de la ventana sigue el mismo camino que ESC: desactiva el
        # toggle de la toolbar (que llama a exit() -> hide()) y devuelve True
        # para evitar el destroy por defecto que crashea en WSLg/GTK3.
        parent.boss.mpanel.toolbar.get_nth_item(4).set_active(False)
        return True

    def exit(self):
        # No destruir: ocultar y conservar la instancia retenida en
        # da.cycleselector para reutilizarla (make_cycleswin la re-muestra).
        # Destruir este dialogo con ESC/X en GTK3 provocaba un segfault que
        # mataba toda la app; al no destruirlo NUNCA durante la sesion se
        # evita por completo el camino de finalizacion que crasheaba. Se oculta
        # ANTES de redraw: asi get_visible()==False y el redraw/sync posterior
        # no reintroduce cambios de fecha via on_spin_changed.
        self.hide()
        self.parnt.da.redraw()
