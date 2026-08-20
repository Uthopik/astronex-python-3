# -*- coding: utf-8 -*-
import re
import time

from gi.repository import Gtk, Gdk, GLib


class SearchView(Gtk.TreeView):
    def __init__(self, model):
        Gtk.TreeView.__init__(self, model=model)
        self.set_enable_search(False)
        self.connect('start-interactive-search', self.on_search_start)
        self.connect('button-press-event', self.on_buttonpress)
        self.connect('key-press-event', self.on_keypress)
        self.searchbox_on = False
        self.search_win = None
        self.search_entry = None
        self.start_time = 0
        self.timeout_handle = 0

    def on_search_start(self, view):
        if not self.searchbox_on:
            self.interactive_search(view)

    def interactive_search(self, view, key=''):
        self.searchbox_on = True
        # La ventana de busqueda se crea UNA vez y se REUTILIZA (oculta/muestra)
        # en vez de crear+destruir una toplevel en cada busqueda: destruir una
        # toplevel en GTK3/WSLg provoca un segfault.
        if self.search_win is None:
            search_win = Gtk.Window()
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            search_win.add(vbox)
            search_win.set_modal(False)
            search_win.set_decorated(False)
            # Dar parent para que el WM pueda posicionarla (evita el aviso de GTK3
            # sobre ventana sin parent, Errores2 #8).
            try:
                toplevel = view.get_toplevel()
                if isinstance(toplevel, Gtk.Window):
                    search_win.set_transient_for(toplevel)
            except Exception:
                pass
            # La X (delete-event) OCULTA, nunca destruye (return True).
            search_win.connect('delete-event', lambda w, e: (w.hide() or True))

            frame = Gtk.Frame()
            vbox.pack_start(frame, False, False, 0)
            search_entry = Gtk.Entry()
            frame.add(search_entry)
            search_entry.connect('key-press-event', self.on_entry_keypress)
            search_entry.connect('button-press-event', self.on_entry_buttonpress)
            self.search_win = search_win
            self.search_entry = search_entry
        else:
            search_win = self.search_win
            search_entry = self.search_entry

        view.set_search_entry(search_entry)
        view.set_search_column(0)
        search_entry.set_text(key)

        search_win.show_all()
        self.set_searchwin_pos(search_entry)
        search_entry.set_position(-1)

        self.start_time = time.time()
        self.timeout_handle = GLib.timeout_add(1000, self.check_idle)

    def on_entry_keypress(self, entry, event):
        if event.keyval == Gdk.KEY_Return or event.keyval == Gdk.KEY_Escape:
            self.destroy_searchwin()
        return False

    def on_buttonpress(self, view, event):
        if self.searchbox_on:
            self.destroy_searchwin()

    def destroy_searchwin(self):
        # OCULTAR (no destruir): la ventana se retiene en self.search_win y se
        # reutiliza en interactive_search. Destruir una toplevel en GTK3/WSLg
        # provoca un segfault.
        self.set_search_entry(None)
        if self.search_win is not None:
            self.search_win.hide()
        self.searchbox_on = False
        self.grab_focus()

    def set_searchwin_pos(self, search_entry):
        parent = self.get_parent()
        while not isinstance(parent, Gtk.Window):
            parent = parent.get_parent()
        win_x, win_y = parent.get_position()
        my_alloc = self.get_allocation()
        entry_alloc = search_entry.get_allocation()
        x = win_x + my_alloc.width - entry_alloc.width
        y = win_y + my_alloc.height + my_alloc.y
        self.search_win.move(x, y)

    def on_keypress(self, view, event):
        if event.keyval > 255 or event.keyval < 32:
            return False
        if event.state & Gdk.ModifierType.CONTROL_MASK:
            return False
        if re.match('[a-zA-Z\\s]', chr(event.keyval)):
            self.interactive_search(view, chr(event.keyval))
            return True
        return False

    def on_entry_buttonpress(self, entry, event):
        self.start_time = time.time()

    def check_idle(self):
        elapsed_time = time.time() - self.start_time
        if elapsed_time > 3:
            GLib.source_remove(self.timeout_handle)
            self.destroy_searchwin()
            return False
        return True
