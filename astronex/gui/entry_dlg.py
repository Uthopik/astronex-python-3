# -*- coding: utf-8 -*-
from copy import copy
from datetime import datetime, time, timezone

from gi.repository import Gtk

from astronex.gui.datewidget import DateEntry
from astronex.gui.localwidget import LocWidget
from astronex.gui.mainnb import Slot
from astronex.utils import parsestrtime
from astronex.extensions.path import path


class PersonTable(Gtk.Table):
    def __init__(self, current):
        Gtk.Table.__init__(self, n_rows=2, n_columns=2)
        self.curr = current
        lbl = Gtk.Label(label=_('Nombre:'))
        self.attach(lbl, 0, 1, 0, 1)
        lbl = Gtk.Label(label=_('Apellidos:'))
        self.attach(lbl, 0, 1, 1, 2)
        self.first = Gtk.Entry()
        self.first.connect('changed', self.on_changed)
        self.attach(self.first, 1, 2, 0, 1)
        self.last = Gtk.Entry()
        self.last.connect('changed', self.on_changed)
        self.attach(self.last, 1, 2, 1, 2)
        self.set_border_width(3)

    def on_changed(self, w):
        if w is self.first:
            self.curr.person.first = w.get_text()
        elif w is self.last:
            self.curr.person.last = w.get_text()


class EntryDlg(Gtk.Dialog):
    '''New chart inputs dialog'''

    def __init__(self, parent, calc=False):
        self.boss = parent.boss
        self.parent_win = parent
        opts = self.boss.opts
        curr = self.boss.state
        self.curr = curr
        curr.person.set_first(True)
        appath = self.boss.app.appath
        self.last_loaded = None

        # Sin destroy_with_parent: el dialogo se oculta y se reutiliza (winnex.entry),
        # nunca se destruye durante la sesion (evita el segfault de GTK3/WSLg).
        Gtk.Dialog.__init__(self,
                            title=_("Entradas"),
                            transient_for=parent)
        self.connect('configure-event', self.on_configure_event)

        self.set_size_request(400, 580)
        content = self.get_content_area()
        content.set_border_width(3)

        if curr.curr_op != 'draw_local':
            self.pframe = Gtk.Frame(label=_("Personal"))
            self.pframe.set_border_width(3)
            self._person_table = PersonTable(curr)
            self.pframe.add(self._person_table)
            content.pack_start(self.pframe, False, False, 0)

            dw_frame = self.create_datewidget()
            content.pack_start(dw_frame, False, False, 0)
            self.dw = dw_frame.get_child()

        loc_frame = self.create_locwidget()
        content.pack_start(loc_frame, True, True, 0)
        self.loc = loc_frame.get_child()

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        def add_button(name, callback, end=False, size=None):
            but = Gtk.Button()
            img = Gtk.Image()
            imgfile = path.joinpath(appath, "astronex/resources/" + name)
            img.set_from_file(str(imgfile))
            but.set_image(img)
            if size is not None:
                but.set_size_request(size, -1)
            but.connect('clicked', callback)
            if end:
                hbox.pack_end(but, False, False, 0)
            else:
                hbox.pack_start(but, False, False, 0)
            return but

        add_button("stock_refresh.png", self.on_refesh_clicked)
        add_button("gtk-clear.png", self.on_clear_clicked)
        add_button("gtk-save.png", lambda b: self.dlg_response(b, self, 'save', parent), end=True, size=80)
        add_button("gtk-cancel.png", lambda b: self.dlg_response(b, self, 'cancel', parent), end=True, size=80)

        content.pack_end(hbox, False, False, 0)
        self.connect("response", self.quit_response, parent)
        # CRITICO: ocultar desde el handler de 'response' NO impide que GTK
        # DESTRUYA el dialogo al cerrarlo con ESC o con la X. El destroy no lo
        # hace ningun handler, lo hace gtk_main_do_event(): si la emision de
        # 'delete-event' devuelve FALSE, llama a gtk_widget_destroy(). El
        # handler de clase de GtkDialog emite 'response' con DELETE_EVENT y
        # devuelve FALSE a proposito ("do the destroy by default"), asi que el
        # dialogo quedaba oculto Y destruido, mientras winnex.entry seguia
        # apuntando al cadaver: al reabrirlo GTK escupia la cascada de
        # 'assertion GTK_IS_CONTAINER/BOX/BUTTON_BOX failed' y se pintaba un
        # CUADRO NEGRO (bug reportado por Elias).
        # connect_after: el handler de clase se ejecuta igual (sigue emitiendo
        # 'response' una sola vez -> quit_response), pero el valor final de la
        # emision pasa a ser True y gtk_main_do_event ya no destruye nada.
        self.connect_after('delete-event', self.on_delete_keep_alive)
        self.show_all()

        wpos = self.get_position()
        self.pos_x = wpos[0]
        self.pos_y = wpos[1]

    def on_delete_keep_alive(self, widget, event):
        # Ver la nota de __init__: True = "evento ya atendido", impide el
        # destroy por defecto. El dialogo ya lo oculto quit_response.
        return True

    def on_configure_event(self, widget, event):
        self.pos_x = event.x
        self.pos_y = event.y

    def quit_response(self, dialog, rid, parent):
        curr = self.curr
        main = self.boss.mpanel
        active = main.active_slot
        if curr.curr_chart.first == _('Momento actual'):
            chart = curr.now
        else:
            chart = curr.get_active(active)
            if not curr.is_valid(active):
                chart = curr.now
            self.boss.da.panel.nowbut.emit('clicked')
        main.actualize_pool(active, chart)
        # No destruir el dialogo (destroy() en GTK3/WSLg provoca segfault al
        # cerrar con ESC/X). Ocultar y conservar la instancia en parent.entry
        # para reutilizarla; el lanzador la vuelve a mostrar con show_all()+present().
        dialog.hide()

    def dlg_response(self, but, dialog, rid, parent):
        curr = self.curr
        main = self.boss.mpanel
        active = main.active_slot
        chart = curr.get_active(active)
        if rid == 'save' and hasattr(self, 'dw'):
            self.dw.timeentry.emit('changed')
            curr.setchart()
            id, table = main.browser.new_chart(curr.calc)
            if id:
                curr.datab.load_chart(table, id, chart)
        if not curr.is_valid(active):
            chart = curr.now
        else:
            curr.add_to_pool(copy(chart), Slot.overwrite)
        main.actualize_pool(active, chart)
        self.boss.da.redraw()
        self.boss.da.panel.nowbut.emit('clicked')
        # Igual que en quit_response: ocultar (no destruir) y conservar la
        # instancia para reutilizarla. Evita el segfault de finalizacion en WSLg.
        dialog.hide()

    def create_datewidget(self):
        dw = DateEntry(self.boss)
        dt = datetime.now()
        ld = dt.replace(tzinfo=timezone.utc)
        dw.set_date(ld.date())
        dw.set_time(ld.time())
        dw.set_border_width(3)

        frame = Gtk.Frame(label=_("Fecha y hora"))
        frame.set_border_width(3)
        frame.add(dw)
        return frame

    def create_locwidget(self):
        loc = LocWidget()
        frame = Gtk.Frame(label=_("Localidad"))
        frame.set_border_width(3)
        frame.add(loc)
        return frame

    def modify_entries(self, chart):
        curr = self.curr
        self.last_loaded = chart
        if curr and curr.curr_op != 'draw_local':
            table = self._person_table
            table.first.set_text(chart.first)
            table.last.set_text(chart.last)
            date, thistime = parsestrtime(chart.date)
            thistime = thistime.split(' ')[0]
            self.dw.set_date(datetime(*reversed(list(map(int, date.split('/'))))))
            self.dw.set_time(time(*list(map(int, thistime.split(':')))))

        loc = self.loc
        if chart.country == 'USA':
            if not loc.check.get_active():
                loc.check.set_active(True)
            ix = chart.region.index('(')
            reg, state = chart.region[:ix].strip(), chart.region[ix:]
            state = state[1:-1]
        else:
            if loc.check.get_active():
                loc.check.set_active(False)
            reg = chart.region
            state = t(chart.country)
        for r in loc.country_combo.get_model():
            if r[0] == state:
                loc.country_combo.set_active_iter(r.iter)
                break
        loc.reg_combo.get_child().set_text(reg)

        model = loc.locview.get_model()
        it = model.get_iter("0")
        i = 0
        while it:
            city = model.get(it, 0)[0]
            if city == chart.city:
                break
            i += 1
            it = model.iter_next(it)
        loc.locview.set_cursor(Gtk.TreePath.new_from_indices([i]))
        loc.locview.scroll_to_cell(Gtk.TreePath.new_from_indices([i]))

    def on_refesh_clicked(self, but):
        self.loc.set_default_local()

    def on_clear_clicked(self, but):
        if self.last_loaded:
            self.modify_entries(self.last_loaded)
        else:
            self.curr.set_now()
            self.modify_entries(self.curr.now)
