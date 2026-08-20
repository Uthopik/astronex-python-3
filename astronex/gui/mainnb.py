# -*- coding: utf-8 -*-
import sys
import os
from copy import copy

from gi.repository import Gtk, Gdk, GLib, Pango

from astronex.extensions.path import path
from astronex.countries import cata_reg
from astronex.utils import parsestrtime, format_longitud, format_latitud
from astronex.gui.oppanel import OpPanel
from astronex.gui.searchview import SearchView


def _boss():
    from astronex.boss import boss
    return boss


def _curr():
    return _boss().get_state()


def _is_dark_theme():
    env_theme = os.environ.get('GTK_THEME', '') or ''
    if 'dark' in env_theme.lower():
        return True
    settings = Gtk.Settings.get_default()
    if settings is None:
        return False
    if settings.get_property('gtk-application-prefer-dark-theme'):
        return True
    name = settings.get_property('gtk-theme-name') or ''
    return 'dark' in name.lower()


def _set_bg(widget, hex_color):
    if _is_dark_theme():
        return
    rgba = Gdk.RGBA()
    rgba.parse(hex_color)
    widget.override_background_color(Gtk.StateFlags.NORMAL, rgba)


def _combo_text(combo):
    """get_active_text() equivalente para ComboBox con entry."""
    it = combo.get_active_iter()
    if it is not None:
        return combo.get_model()[it][0]
    child = combo.get_child()
    if child is not None:
        return child.get_text()
    return ""


class Slot(Gtk.Box):
    overwrite = False
    storage = None

    def __init__(self, id):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        boss = _boss()
        appath = boss.app.appath

        self.imgfile1 = path.joinpath(appath, "astronex/resources/stock_inbox-24.png")
        self.imgfile2 = path.joinpath(appath, "astronex/resources/gtk-folder-24.png")

        self.wname = id
        self.chart_id = None
        self.timeout_sid = None
        names = ['master', 'click']
        names.remove(self.wname)
        self.other = names.pop()
        self.prev_clock_button = None
        self.prev_showpe = False
        self.swap = ['click', 'master']

        table = Gtk.Table(n_rows=4, n_columns=2)
        hbutbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        but = Gtk.Button()
        img = Gtk.Image()
        if self.wname == 'master':
            img.set_from_file(str(self.imgfile1))
        else:
            img.set_from_file(str(self.imgfile2))
        but.set_image(img)
        but.connect('clicked', self.on_storage_clicked)
        but.set_tooltip_text(_('Alternar almacenamiento maestro/clic'))
        hbutbox.pack_start(but, True, True, 0)
        self.storage_img = img
        self.storage_but = but
        table.attach(hbutbox, 0, 1, 0, 1)

        hbutbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        but = Gtk.Button()
        img = Gtk.Image()
        imgfile = path.joinpath(appath, "astronex/resources/drivel-24.png")
        img.set_from_file(str(imgfile))
        but.set_image(img)
        but.connect('clicked', self.on_entry_clicked)
        self.mod = but
        but.set_tooltip_text(_('Modificar carta'))
        hbutbox.pack_end(but, False, False, 0)
        but = Gtk.Button()
        img = Gtk.Image()
        imgfile = path.joinpath(appath, "astronex/resources/clock-24.png")
        img.set_from_file(str(imgfile))
        but.set_image(img)
        but.connect('clicked', self.on_clock_clicked)
        self.clock = but
        but.set_tooltip_text(_('Carta del momento'))
        hbutbox.pack_end(but, False, False, 0)
        ev = Gtk.EventBox()
        img = Gtk.Image()
        imgfile = path.joinpath(appath, "astronex/resources/gnome-eog-24.png")
        img.set_from_file(str(imgfile))
        ev.add(img)
        _set_bg(ev, "white")
        hbutbox.pack_end(ev, True, True, 0)
        ev.set_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        ev.connect("button-press-event", self.on_eye_clicked)
        ev.set_tooltip_text(_('Personas recientes y favoritos'))
        self.eye = ev
        table.attach(hbutbox, 1, 2, 0, 1)

        self.namelbl = Gtk.Label(label=_("Nombre"))
        self.namelbl.set_property('xalign', 0.0)
        table.attach(self.namelbl, 0, 2, 1, 2)
        self.datelbl = Gtk.Label(label=_("Fecha"))
        self.datelbl.set_property('xalign', 0.0)
        table.attach(self.datelbl, 0, 2, 2, 3)
        self.loclbl = Gtk.Label(label=_("Localidad"))
        self.loclbl.set_property('xalign', 0.0)
        self.loclbl.set_ellipsize(Pango.EllipsizeMode.END)
        table.attach(self.loclbl, 0, 1, 3, 4)
        self.reglbl = Gtk.Label(label=_("Region"))
        self.reglbl.set_property('xalign', 0.0)
        self.reglbl.set_ellipsize(Pango.EllipsizeMode.END)
        table.attach(self.reglbl, 1, 2, 3, 4)
        table.set_border_width(2)
        eb = Gtk.EventBox()
        eb.add(table)
        _set_bg(eb, "white")

        self.pack_start(eb, True, True, 0)
        self.eb = eb

        self.menu = Gtk.Menu()
        for buf in (_('Exportar carta'), _('Importar carta')):
            menu_items = Gtk.MenuItem(label=buf)
            self.menu.append(menu_items)
            menu_items.connect("activate", self.on_menuitem_activate)
            menu_items.show()
        self.set_events(self.get_events() | Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.SCROLL_MASK)
        self.connect("button-press-event", self.on_slot_clicked)
        self.connect('scroll-event', self.on_scroll_event)
        self.set_size_request(320, -1)

    def on_entry_clicked(self, but):
        curr = _curr()
        boss = _boss()
        if self.chart_id != 'now':
            widget = MainPanel.pool[self.wname]
            MainPanel.slot_activate(widget)
        chart = curr.charts[self.chart_id]
        mainwin = boss.mainwin
        if not mainwin.entry:
            mainwin.activate_entry()
        else:
            # El dialogo ahora se oculta (no se destruye) al cerrarlo, asi que
            # mainwin.entry sigue existiendo; hay que re-mostrarlo explicitamente
            # porque activate_entry() solo se invoca cuando entry es None.
            mainwin.entry.show_all()
            mainwin.entry.present()
        mainwin.entry.modify_entries(chart)

    def on_eye_clicked(self, eye, event):
        curr = _curr()
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
            names = []
            for ch in curr.pool:
                names.append(" ".join([ch.first, ch.last]))
            menu = Gtk.Menu()
            ow = Gtk.CheckMenuItem(label=_('Sobrescribir'))
            ow.set_active(Slot.overwrite)
            ow.connect('toggled', self.on_ow_toggled)
            menu.append(ow)
            ow.show()
            sep_item = Gtk.SeparatorMenuItem()
            menu.append(sep_item)
            sep_item.show()
            for i, ch in enumerate(curr.fav):
                name = " ".join([ch.first, ch.last])
                menu_item = Gtk.MenuItem(label=name)
                menu.append(menu_item)
                menu_item.connect("activate", self.on_fav_menu_activate, menu, i)
                menu_item.show()
            if curr.fav:
                sep_item = Gtk.SeparatorMenuItem()
                menu.append(sep_item)
                sep_item.show()
            for buf in names:
                menu_items = Gtk.MenuItem(label=buf)
                menu.append(menu_items)
                menu_items.connect("activate", self.on_eye_menu_activate, menu)
                menu_items.show()
            menu.popup_at_pointer(event)
            return True

    def on_ow_toggled(self, check):
        Slot.overwrite = check.get_active()

    def on_fav_menu_activate(self, menuitem, menu, ix):
        curr = _curr()
        active = Slot.storage
        curr.load_from_fav(ix, active)
        MainPanel.actualize_pool(active, curr.charts[active])
        menu.popdown()

    def on_eye_menu_activate(self, menuitem, menu):
        curr = _curr()
        active = Slot.storage
        ix = 0
        name = menuitem.get_label()
        for i, ch in enumerate(list(curr.pool)):
            if " ".join([ch.first, ch.last]) == name:
                ix = i
                break
        if curr.load_from_pool(ix, active):
            MainPanel.actualize_pool(active, curr.charts[active])
        menu.popdown()

    def on_clock_clicked(self, but):
        curr = _curr()
        boss = _boss()
        # Momento actual: re-aplicar la localidad POR DEFECTO de la configuracion.
        # Al trabajar con una persona, setprogchart deja curr.loc en la ciudad de
        # esa persona (p.ej. Donostia); sin esto la carta del momento heredaba esa
        # localidad en vez de la configurada. init_nowchart() es el mismo camino
        # del arranque: set_now() (fecha = momento real) + refresh_nowchart()
        # (copia ciudad/region/zona de curr.loc, ya la por defecto, y recalcula).
        curr.setloc(boss.opts.locality, boss.opts.region)
        curr.init_nowchart()
        widget = MainPanel.pool[self.wname]
        MainPanel.slot_activate(widget)
        MainPanel.actualize_pool(self.wname, curr.now)
        self.prev_clock_button = boss.mpanel.chooser.current_button
        boss.mpanel.chooser.init_button.emit('clicked')
        active = boss.mpanel.toolbar.get_nth_item(1).get_active()
        self.prev_showpe = active
        boss.mpanel.toolbar.get_nth_item(1).set_active(False)

    def on_storage_clicked(self, but):
        other = MainPanel.pool[self.other]
        self.storage_img.set_from_file(str(self.imgfile1))
        other.storage_img.set_from_file(str(self.imgfile2))
        _set_bg(self.storage_but, "white")
        _set_bg(other.storage_but, "#f6f7fe")
        MainPanel.browser.slot = self.wname
        Slot.storage = self.wname

    def on_slot_clicked(self, slot, event):
        curr = _curr()
        boss = _boss()
        self.x, self.y = event.x, event.y
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            self.menu.popup_at_pointer(event)
            return True
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
            if self.wname != MainPanel.active_slot:
                other = MainPanel.pool[self.other]
                _set_bg(self.eb, "white")
                _set_bg(other.eb, "#f6f7fe")
                self.eye.show()
                other.eye.hide()
                curr.curr_chart, curr.curr_click = curr.curr_click, curr.curr_chart
                curr.crossed = not curr.crossed
                boss.redraw()
                boss.da.redraw_auxwins()
            elif self.chart_id == 'now':
                chart = curr.charts[self.wname]
                if curr.is_valid(chart.id):
                    MainPanel.actualize_pool(self.wname, chart)
                try:
                    self.prev_clock_button.emit('clicked')
                except AttributeError:
                    pass
            MainPanel.active_slot = self.wname
            if self.chart_id == 'now':
                boss.mpanel.toolbar.get_nth_item(1).set_active(False)
            elif self.prev_showpe:
                boss.mpanel.toolbar.get_nth_item(1).set_active(True)
            if boss.da.cycleselector:
                boss.da.cycleselector.refresh_spin()
            return True
        return True

    def on_menuitem_activate(self, menuitem):
        curr = _curr()
        label = menuitem.get_label()
        if label == _('Exportar carta'):
            widget = MainPanel.pool[self.wname]
            MainPanel.slot_activate(widget)
            chart = curr.charts[self.chart_id]
            folder = os.path.expanduser("~") + os.path.sep
            name = "_".join((chart.first, chart.last)).strip().replace(" ", "_")
            name = folder + name + ".nx1"
            with open(name, 'w', encoding='utf-8') as f:
                f.write(chart.__repr__())
        else:
            dialog = Gtk.FileChooserDialog(
                title=_("Importar carta"),
                parent=None,
                action=Gtk.FileChooserAction.OPEN)
            dialog.add_buttons(_("_Cancelar"), Gtk.ResponseType.CANCEL,
                               _("_Abrir"), Gtk.ResponseType.OK)
            dialog.set_default_response(Gtk.ResponseType.OK)
            dialog.set_current_folder(os.path.expanduser("~"))
            dialog.set_show_hidden(False)
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                filename = dialog.get_filename()
                with open(filename, encoding='utf-8') as f:
                    data = f.read().split(",")
                chart = curr.charts[self.wname]
                try:
                    curr.load_import(chart, data)
                    MainPanel.actualize_pool(self.wname, chart)
                except Exception:
                    msg = _('Error importando carta')
                    err = Gtk.MessageDialog(transient_for=None, modal=True,
                                            message_type=Gtk.MessageType.ERROR,
                                            buttons=Gtk.ButtonsType.OK,
                                            text=msg)
                    err.run()
                    err.hide()  # no destruir toplevel (segfault GTK3/WSLg); ocultar
            dialog.hide()

    def on_scroll_event(self, entry, event):
        curr = _curr()
        if event.direction == Gdk.ScrollDirection.UP:
            delta = 1
        elif event.direction == Gdk.ScrollDirection.DOWN:
            delta = -1
        elif event.direction == Gdk.ScrollDirection.SMOOTH:
            ok, dx, dy = event.get_scroll_deltas()
            if not ok or dy == 0:
                return
            delta = 1 if dy < 0 else -1
        else:
            return
        if curr.load_from_pool(delta, self.wname):
            MainPanel.actualize_pool(self.wname, curr.charts[self.wname])


class ChartBrowser(Gtk.Box):
    def __init__(self, ap_path, font):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        curr = _curr()
        self.chartview = None
        self.font = font
        appath = path.joinpath(ap_path, 'astronex')

        liststore = Gtk.ListStore(str)
        self.tables = Gtk.ComboBox.new_with_model_and_entry(liststore)
        self.tables.set_entry_text_column(0)
        self.entry = self.tables.get_child()
        self.entry.set_editable(False)
        self.entry.connect('activate', self.on_search_activated)

        self.tables.connect('changed', self.on_tables_changed)
        self.tables.set_size_request(120, -1)
        tablelist = curr.datab.get_databases()
        liststore.append([_('(Buscar)')])

        for c in tablelist:
            liststore.append([c])
        index = 0
        for i, r in enumerate(liststore):
            if r[0] == curr.database:
                index = i
                break
        self.tables.set_active(index)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.pack_start(self.tables, True, True, 0)

        opbut = Gtk.Button()
        img = Gtk.Image()
        imgfile = path.joinpath(appath, "resources/folder-convert24.png")
        img.set_from_file(str(imgfile))
        opbut.set_image(img)
        opbut.set_tooltip_text(_('Explorador/Tablas'))
        opbut.connect('clicked', self.on_opbut_clicked)
        hbox.pack_start(opbut, False, False, 0)

        opbut = Gtk.Button()
        img = Gtk.Image()
        imgfile = path.joinpath(appath, "resources/pgram.png")
        img.set_from_file(str(imgfile))
        opbut.set_image(img)
        opbut.set_tooltip_text(_('Planetograma'))
        opbut.connect('clicked', self.on_plagram_clicked)
        hbox.pack_start(opbut, False, False, 0)
        self.pack_start(hbox, False, False, 0)

        self.chartmodel = Gtk.ListStore(str, int)
        self.chartview = SearchView(self.chartmodel)
        selection = self.chartview.get_selection()
        selection.set_mode(Gtk.SelectionMode.SINGLE)
        chartlist = curr.datab.get_chartlist(_combo_text(self.tables))

        for c in chartlist:
            glue = ", "
            if c[2] == '':
                glue = ''
            self.chartmodel.append([c[2] + glue + c[1], int(c[0])])

        cell = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(None, cell, text=0)
        self.chartview.append_column(column)
        self.chartview.set_headers_visible(False)
        self.chartview.connect('row-activated', self.on_chart_activated)

        self.menu = Gtk.Menu()
        for buf in (_('Copiar'), _('Cortar'), _('Pegar')):
            menu_items = Gtk.MenuItem(label=buf)
            self.menu.append(menu_items)
            menu_items.connect("activate", self.on_menuitem_activate, buf)
            menu_items.show()
        self.chartview.connect('button-press-event', self.on_view_clicked)

        self.clip = None

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.add(self.chartview)
        self.pack_start(sw, True, True, 0)

    def on_opbut_clicked(self, but):
        _boss().mainwin.launch_chartbrowser_from_mpanel()

    def on_plagram_clicked(self, but):
        _boss().mainwin.launch_plagram(None, None, None, None)

    def relist(self, new):
        curr = _curr()
        liststore = Gtk.ListStore(str)
        tablelist = curr.datab.get_databases()
        for c in tablelist:
            liststore.append([c])
        if not new:
            new = _combo_text(self.tables)
        index = 0
        for i, r in enumerate(liststore):
            if r[0] == new:
                index = i
                break
        self.tables.set_model(liststore)
        self.tables.set_active(index)

    def on_view_clicked(self, view, event):
        curr = _curr()
        boss = _boss()
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 2:
            pthinfo = view.get_path_at_pos(int(event.x), int(event.y))
            if not pthinfo:
                return True
            tree_path = pthinfo[0]
            view.get_selection().select_path(tree_path)
            model, it = view.get_selection().get_selected()
            if not it:
                return True
            id = model.get_value(it, 1)
            try:
                table = model.get_value(it, 2)
            except ValueError:
                table = _combo_text(self.tables)
            chart = curr.newchart()
            curr.datab.load_chart(table, id, chart)
            boss.mainwin.launch_aux_from_browser(chart)
            return True
        elif event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            x = int(event.x)
            y = int(event.y)
            pthinfo = view.get_path_at_pos(x, y)
            if pthinfo is not None:
                tree_path, col, cellx, celly = pthinfo
                view.grab_focus()
                view.set_cursor(tree_path, col, False)
                if self.clip is None:
                    self.menu.get_children()[2].set_sensitive(False)
                self.menu.popup_at_pointer(event)
            return True
        return False

    def on_menuitem_activate(self, menuitem, item):
        curr = _curr()
        model, it = self.chartview.get_selection().get_selected()
        id = model.get_value(it, 1)
        table = _combo_text(self.tables)
        if item == _('Copiar') or item == _('Cortar'):
            chart = curr.newchart()
            curr.datab.load_chart(table, id, chart)
            self.clip = chart
            menuitem.get_parent().get_children()[2].set_sensitive(True)
            if item == _('Cortar'):
                if not curr.safe_delete_chart(table, id):
                    msg = _('No puedo eliminar una carta con pareja!')
                    dlg = Gtk.MessageDialog(transient_for=None, modal=True,
                                            message_type=Gtk.MessageType.WARNING,
                                            buttons=Gtk.ButtonsType.OK,
                                            text=msg)
                    dlg.run()
                    dlg.hide()  # no destruir toplevel (segfault GTK3/WSLg); ocultar
                    return
                curr.datab.delete_chart(table, id)
                self.tables.emit('changed')
        else:
            self.new_chart(self.clip)

    def on_search_activated(self, entry):
        curr = _curr()
        if self.tables.get_active() > 0:
            return
        searchlist = curr.datab.search_by_name_all_tables(entry.get_text())
        if self.chartview is not None:
            chartmodel = Gtk.ListStore(str, int, str)
            for c in searchlist:
                glue = ", "
                if c[3] == '':
                    glue = ''
                chartmodel.append([c[3] + glue + c[2], int(c[1]), c[0]])
            self.chartview.set_model(chartmodel)

    def on_tables_changed(self, combo):
        curr = _curr()
        if combo.get_active() == -1:
            return
        if combo.get_active() == 0:
            self.entry.set_editable(True)
            self.entry.select_region(0, -1)
            self.entry.grab_focus()
            return
        else:
            if self.entry.get_editable():
                self.entry.set_editable(False)

        if self.chartview is not None:
            chartmodel = Gtk.ListStore(str, int)
            chartlist = curr.datab.get_chartlist(_combo_text(self.tables))
            i = 0
            r = 0
            for c in chartlist:
                glue = ", "
                if c[2] == '':
                    glue = ''
                chartmodel.append([c[2] + glue + c[1], int(c[0])])
                if curr.curr_chart.first == c[1] and curr.curr_chart.last == c[2]:
                    r = i
                i += 1
            self.chartview.set_model(chartmodel)
            self.chartview.get_selection().select_path(Gtk.TreePath.new_from_indices([r]))
            self.chartview.scroll_to_cell(Gtk.TreePath.new_from_indices([r]))

    def on_chart_activated(self, view, path, col):
        curr = _curr()
        # Usar la fila ACTIVADA (path) sobre el modelo actual, no la seleccion,
        # que puede quedar desincronizada tras recargar el modelo.
        model = view.get_model()
        try:
            it = model.get_iter(path)
        except (ValueError, TypeError):
            return
        if it is None:
            return
        id = model.get_value(it, 1)
        if model.get_n_columns() > 2:
            table = model.get_value(it, 2)
        else:
            table = _combo_text(self.tables)
        chart = curr.charts[self.slot]
        if not curr.datab.load_chart(table, id, chart):
            return  # carta no encontrada: no continuar con datos invalidos
        curr.add_to_pool(copy(chart), Slot.overwrite)
        MainPanel.actualize_pool(self.slot, chart)

    def constrainterror_dlg(self, fi, la):
        msg = _("Una carta con este nombre: %s %s existe. Sobrescribir?") % (fi, la)
        dialog = Gtk.MessageDialog(transient_for=None, modal=True,
                                   message_type=Gtk.MessageType.WARNING,
                                   buttons=Gtk.ButtonsType.OK_CANCEL,
                                   text=msg)
        result = dialog.run()
        dialog.hide()  # no destruir toplevel (segfault GTK3/WSLg); ocultar
        return result

    def new_chart(self, chart):
        curr = _curr()
        from sqlite3 import DatabaseError
        table = _combo_text(self.tables)
        try:
            lastrow = curr.datab.store_chart(table, chart)
        except DatabaseError:
            result = self.constrainterror_dlg(chart.first, chart.last)
            if result != Gtk.ResponseType.OK:
                return None, None
            curr.datab.delete_chart_from_name(table, chart.first, chart.last)
            lastrow = curr.datab.store_chart(table, chart)
            curr.fix_couples(table, chart.first, chart.last, lastrow)
        self.tables.emit('changed')
        return lastrow, table


class MainPanel(Gtk.Box):
    pool = {}
    active_slot = ''
    timeout_sid = None

    def __init__(self, manager):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, homogeneous=False)
        self.boss = manager
        appath = manager.app.appath

        frame = Gtk.Frame()
        widget = Slot("master")
        MainPanel.pool['master'] = widget
        frame.add(widget)
        self.pack_start(frame, False, False, 0)

        frame = Gtk.Frame()
        widget = Slot("click")
        MainPanel.pool['click'] = widget
        frame.add(widget)
        self.pack_start(frame, False, False, 0)

        frame = Gtk.Frame()
        browser = ChartBrowser(appath, manager.opts.font)
        MainPanel.browser = browser
        frame.add(browser)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.pack_start(frame, True, True, 0)
        tb = self.make_toolbar(appath, manager)
        frame = Gtk.Frame()
        frame.add(tb)
        self.toolbar = tb
        hbox.pack_start(frame, False, False, 0)
        hbox.set_size_request(-1, 390)
        self.pack_start(hbox, False, False, 0)

        self.chooser = OpPanel(manager)
        self.pack_end(self.chooser, True, True, 0)

    def make_toolbar(self, appath, boss):
        appath = path.joinpath(appath, 'astronex')
        tb = Gtk.Toolbar()
        tb.set_orientation(Gtk.Orientation.VERTICAL)
        tb.set_size_request(-1, 24)
        tb.set_style(Gtk.ToolbarStyle.ICONS)
        tb.set_show_arrow(True)

        def add_toggle(name, callback, tooltip):
            tb_item = Gtk.ToggleToolButton()
            tb_item.connect('toggled', callback, boss)
            img = Gtk.Image()
            imgfile = path.joinpath(appath, "resources/" + name)
            img.set_from_file(str(imgfile))
            tb_item.set_icon_widget(img)
            tb_item.set_tooltip_text(tooltip)
            tb.insert(tb_item, -1)

        def add_button(name, callback, tooltip):
            tb_item = Gtk.ToolButton()
            tb_item.connect('clicked', callback, boss)
            img = Gtk.Image()
            imgfile = path.joinpath(appath, "resources/" + name)
            img.set_from_file(str(imgfile))
            tb_item.set_icon_widget(img)
            tb_item.set_tooltip_text(tooltip)
            tb.insert(tb_item, -1)

        add_toggle("cal.png", self.on_calpanel, _("Calendario"))
        add_toggle("ap.png", self.on_pebut, _("Punto Edad"))
        add_button("new-win.png", self.on_auxwin, _("Ventana auxiliar"))
        add_toggle("aspects.png", self.on_plsel, _("Selector de aspectos"))
        add_toggle("cycles2.png", self.on_cycles, _("Selector de ciclos"))
        add_toggle("subdia.png", self.on_diada, _("Diagramas"))
        add_toggle("bridge.png", self.on_pebridge, _("PE puente"))

        return tb

    def on_calpanel(self, but, boss):
        if but.get_active():
            boss.da.show_panel()
        else:
            boss.da.hide_panel()

    def on_pebut(self, but, boss):
        if but.get_active():
            boss.da.show_pe()
        else:
            boss.da.hide_pe()

    def on_auxwin(self, but, boss):
        boss.da.make_auxwin()

    def on_plsel(self, but, boss):
        if but.get_active():
            boss.da.make_plsel()
        else:
            boss.da.hide_plsel()

    def on_cycles(self, but, boss):
        if but.get_active():
            boss.da.make_cycleswin()
        else:
            boss.da.cycleselector.exit()

    def on_diada(self, but, boss):
        if but.get_active():
            boss.da.show_diada()
        else:
            boss.da.hide_diada()

    def on_pebridge(self, but, boss):
        if but.get_active():
            boss.da.make_pebridge()
        else:
            boss.da.hide_pebridge()

    @classmethod
    def now_timeout(cls):
        curr = _curr()
        curr.set_now()
        cls.act_now(curr.charts['now'])
        return True

    @classmethod
    def start_timeout(cls, tm=5):
        if not cls.timeout_sid:
            _boss().da.panel.nowbut.emit('clicked')
            cls.timeout_sid = GLib.timeout_add(tm * 1000, cls.now_timeout)

    @classmethod
    def stop_timeout(cls):
        if cls.timeout_sid:
            GLib.source_remove(cls.timeout_sid)
            cls.timeout_sid = None

    @staticmethod
    def update_slot_label(slot, chart):
        boss = _boss()
        slot.chart_id = chart.id
        name_color = '#7eb6ff' if _is_dark_theme() else 'blue'
        slot.namelbl.set_markup("<span foreground='" + name_color + "'>" + chart.first + ' ' + chart.last + "</span>")
        strdate = chart.date
        date, time = parsestrtime(strdate)
        slot.loclbl.set_text(chart.city)
        region = chart.region
        if boss.opts.lang == 'ca' and chart.country == 'España':
            region = cata_reg[region]
        slot.reglbl.set_text(t(chart.country) + ' (' + region + ')')
        geo = format_longitud(chart.longitud) + ' ' + format_latitud(chart.latitud)
        slot.datelbl.set_text(date + ' ' + time + ' ' + geo)

    @classmethod
    def init_pools(cls):
        curr = _curr()
        boss = _boss()
        chart = curr.now
        for slot in ['master', 'click']:
            cls.update_slot_label(cls.pool[slot], chart)
        curr.curr_chart = curr.curr_click = chart
        boss.da.redraw()
        widget = cls.pool['master']
        MainPanel.slot_activate(widget)
        widget.storage_but.emit("clicked")
        if curr.load_from_pool(0, 'click'):
            cls.actualize_pool('click', curr.charts['click'])

    @classmethod
    def act_now(cls, chart):
        curr = _curr()
        master_slot = cls.pool['master']
        click_slot = cls.pool['click']
        if master_slot.chart_id != 'now' and click_slot.chart_id != 'now':
            return

        slot = cls.pool[cls.active_slot]
        if slot.chart_id == 'now':
            cls.update_slot_label(slot, chart)
            curr.curr_chart = chart
        other = cls.pool[slot.other]
        if other.chart_id == 'now':
            cls.update_slot_label(other, chart)
            curr.curr_click = chart

    @staticmethod
    def actualize_pool(slot, chart):
        curr = _curr()
        boss = _boss()
        slot = MainPanel.pool[slot]

        if boss.da.cycleselector and slot.wname == MainPanel.active_slot:
            cycles = chart.get_cycles()
            boss.da.cycleselector.adj.set_value(cycles + 1)

        if slot.wname == MainPanel.active_slot:
            curr.curr_chart = chart
        else:
            curr.curr_click = chart
        MainPanel.update_slot_label(slot, chart)

        if curr.curr_op == "sec_prog":
            boss.da.panel.nowbut.emit('clicked')

        boss.redraw()
        boss.da.redraw_auxwins()

    @staticmethod
    def slot_activate(slot):
        event = Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
        event.button = 1
        event.time = 0
        slot.emit("button-press-event", event)

    @classmethod
    def slot_act_inactive(cls):
        slot = cls.pool[cls.active_slot]
        slot = cls.pool[slot.other]
        cls.slot_activate(slot)

    @classmethod
    def swap_storage(cls):
        slot = cls.pool[Slot.storage]
        slot = cls.pool[slot.other]
        slot.storage_but.emit('clicked')

    @classmethod
    def scroll_pool(cls, delta):
        curr = _curr()
        slot = cls.active_slot
        if curr.load_from_pool(delta, slot):
            cls.actualize_pool(slot, curr.charts[slot])
