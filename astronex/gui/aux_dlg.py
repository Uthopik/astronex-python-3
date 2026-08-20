# -*- coding: utf-8 -*-
from gi.repository import Gtk, Gdk

from astronex.surfaces.sdasurface import DrawAux


class AuxWindow(Gtk.Window):
    def __init__(self, parent, chart=None):
        self.boss = parent.boss
        Gtk.Window.__init__(self)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        # NO usar set_destroy_with_parent: ese camino arrastra la finalizacion
        # (destroy) al cerrar la principal y en WSLg/GTK3 ese destroy segfaultea.
        self.set_title("Astro-Nex")

        accel_group = Gtk.AccelGroup()
        accel_group.connect(Gdk.KEY_Escape, 0, Gtk.AccelFlags.LOCKED, self.escape)
        accel_group.connect(Gdk.KEY_plus, 0, Gtk.AccelFlags.LOCKED, self.house_change)
        accel_group.connect(Gdk.KEY_minus, 0, Gtk.AccelFlags.LOCKED, self.house_change)
        accel_group.connect(Gdk.KEY_Menu, 0, Gtk.AccelFlags.LOCKED, self.popup_menu)
        accel_group.connect(Gdk.KEY_Up, Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.LOCKED, self.fake_scroll_up)
        accel_group.connect(Gdk.KEY_Down, Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.LOCKED, self.fake_scroll_down)
        self.add_accel_group(accel_group)

        self.sda = DrawAux(self.boss, chart)
        self.add(self.sda)

        aux_size = int(self.boss.opts.aux_size)
        self.set_default_size(aux_size, aux_size)
        # ESC o la X = OCULTAR (no destruir). Destruir esta ventana en GTK3/WSLg
        # provocaba un segfault que mataba toda la app. Al no destruirla nunca
        # durante la sesion se evita por completo ese camino de finalizacion.
        # AuxWindow es multi-instancia (varias cartas a la vez en boss.da.auxwins),
        # asi que al cerrar la sacamos de auxwins (deja de redibujarse) y la
        # retenemos oculta en boss.da._aux_hidden para que GTK no la finalice.
        self.connect('delete-event', self.on_delete)
        self.show_all()

    def _close_aux(self):
        auxwins = self.boss.da.auxwins
        if self in auxwins:
            auxwins.remove(self)
        # Retener la instancia oculta: evita que su refcount baje a 0 y que GTK
        # ejecute la finalizacion (destroy) que crashea en WSLg.
        hidden = getattr(self.boss.da, '_aux_hidden', None)
        if hidden is None:
            hidden = []
            self.boss.da._aux_hidden = hidden
        if self not in hidden:
            hidden.append(self)
        self.hide()

    def escape(self, a, b, c, d):
        self._close_aux()
        return True

    def on_delete(self, widget, event):
        # No destruir: ocultar (return True evita el destroy por defecto).
        self._close_aux()
        return True

    def house_change(self, acgroup, actable, keyval, mod):
        if keyval == Gdk.KEY_plus:
            self.boss.da.hsel.get_child().house_updown(1)
        else:
            self.boss.da.hsel.get_child().house_updown(-1)

    def popup_menu(self, acgroup, actable, keyval, mod):
        self.sda.popup_menu()

    def fake_scroll_up(self, acgroup, actable, keyval, mod):
        event = Gdk.Event.new(Gdk.EventType.SCROLL)
        event.scroll.direction = Gdk.ScrollDirection.UP
        self.sda.on_scroll(self.sda, event.scroll)

    def fake_scroll_down(self, acgroup, actable, keyval, mod):
        event = Gdk.Event.new(Gdk.EventType.SCROLL)
        event.scroll.direction = Gdk.ScrollDirection.DOWN
        self.sda.on_scroll(self.sda, event.scroll)
