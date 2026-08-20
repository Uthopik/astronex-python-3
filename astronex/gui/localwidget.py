# -*- coding: utf-8 -*-
import weakref

from gi.repository import Gtk

from astronex.countries import cata_reg
from astronex.gui.searchview import SearchView

# Todos los LocWidget vivos. Hace falta porque el listado de localidades se
# construye UNA vez en __init__ y los dialogos que lo contienen (Entradas,
# selector de localidad) se retienen y se reutilizan durante toda la sesion en
# vez de destruirse. Sin esto, una localidad dada de alta con Ctrl+L no aparecia
# entre las localidades hasta reiniciar el programa.
_widgets_vivos = weakref.WeakSet()


def reload_all_localities():
    """Recarga el listado de localidades de todos los LocWidget abiertos.
    Se llama tras guardar una localidad nueva (customloc_dlg)."""
    for w in list(_widgets_vivos):
        try:
            w.reload_localities()
        except Exception:
            pass


def _get_boss():
    from astronex.boss import boss
    return boss


def _get_curr():
    return _get_boss().get_state()


def filter_region(model, it, code):
    value = model.get_value(it, 1)
    return value == code


class LocWidget(Gtk.Box):
    def __init__(self, default=False):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self.set_homogeneous(False)
        self._recargando = False
        _widgets_vivos.add(self)
        boss = _get_boss()
        curr = _get_curr()

        if not default:
            if curr.usa:
                x, c = curr.loc.region.split('(')
                c = curr.datab.get_usacode_from_name(c[:-1])
                country_code = c
            else:
                country_code = curr.loc.country_code
            region = curr.loc.region_code
            city = curr.loc.city
        else:
            curr.usa = {'false': False, 'true': True}[boss.opts.usa]
            country_code = boss.opts.country
            region = boss.opts.region
            city = boss.opts.locality
            curr.country = country_code

        self.countries = curr.datab.get_states_tuple(curr.usa)
        self.sortlist = sorted(self.countries)

        compl = Gtk.EntryCompletion()

        # country label and check btns
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        l = [_('Pais'), _('Estado')][curr.usa]
        label = Gtk.Label(label=l)
        hbox.pack_start(label, False, False, 0)
        self.check = Gtk.CheckButton(label=_("Usa"))
        self.check.set_active(curr.usa)
        self.check.connect('toggled', self.on_usa_toggled, compl, label)
        hbox.pack_start(self.check, True, False, 0)

        self.filtcheck = Gtk.CheckButton(label=_("Filtro"))
        self.filtcheck.connect('toggled', self.on_filter_toggled)
        hbox.pack_start(self.filtcheck, True, False, 0)
        label = Gtk.Label(label=_('Region'))
        hbox.pack_end(label, True, False, 0)
        hbox.set_border_width(3)
        hbox.set_homogeneous(True)
        self.pack_start(hbox, False, False, 0)

        # country combo (ComboBox con entry — reemplazo de ComboBoxEntry)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        liststore = Gtk.ListStore(str, str)
        self.country_combo = Gtk.ComboBox.new_with_model_and_entry(liststore)
        self.country_combo.set_entry_text_column(0)

        for n, c in self.sortlist:
            liststore.append([n, c])

        for r in self.country_combo.get_model():
            if r[1] == country_code:
                self.country_combo.set_active_iter(r.iter)
                break

        compl.set_text_column(0)
        compl.set_model(self.country_combo.get_model())
        self.country_combo.get_child().set_completion(compl)
        compl.connect('match-selected', self.on_count_match)

        self.country_combo.set_wrap_width(4)
        self.country_combo.connect('changed', self.on_count_selected)
        hbox.pack_start(self.country_combo, False, False, 0)

        # region combo
        liststore = Gtk.ListStore(str, str)
        self.reg_combo = Gtk.ComboBox.new_with_model_and_entry(liststore)
        self.reg_combo.set_entry_text_column(0)
        self.reg_combo.connect('changed', self.on_reg_selected)
        rlist = curr.datab.list_regions(country_code, curr.usa)
        if country_code == "SP" and boss.opts.lang == 'ca':
            rlist = [(cata_reg[r[0]], r[1]) for r in rlist]

        i = 0
        for n, r in enumerate(rlist):
            liststore.append(r)
            if region == r[1]:
                i = n

        self.reg_combo.set_active(i)
        hbox.pack_end(self.reg_combo, False, False, 0)
        self.pack_start(hbox, False, False, 0)

        # locality view
        self.locmodel = Gtk.ListStore(str, str, str)
        self.locview = SearchView(self.locmodel)
        selection = self.locview.get_selection()
        selection.connect('changed', self.on_sel_changed)
        selection.set_mode(Gtk.SelectionMode.SINGLE)
        loclist = curr.datab.fetch_all_from_country(country_code, curr.usa)
        i = 0
        for n, c in enumerate(loclist):
            self.locmodel.append(c)
            if city == c[0]:
                i = n

        cell = Gtk.CellRendererText()
        cell.set_property('width-chars', 38)
        from astronex.gui.mainnb import _is_dark_theme
        cell.set_property('foreground', '#7eb6ff' if _is_dark_theme() else 'blue')
        cellgeo = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn()
        column.pack_start(cell, False)
        column.pack_start(cellgeo, False)
        column.set_attributes(cell, text=0)
        column.set_attributes(cellgeo, text=2)
        column.set_widget(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        self.locview.append_column(column)
        self.locview.set_headers_visible(False)
        self.locview.set_cursor(Gtk.TreePath.new_from_indices([i]), column, False)
        self.locview.scroll_to_cell(Gtk.TreePath.new_from_indices([i]))
        self.locview.connect('row-activated', self.on_row_activate)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.add(self.locview)
        self.pack_start(sw, True, True, 0)

    def reload_localities(self):
        """Vuelve a leer las localidades del pais seleccionado, conservando la
        que estuviera elegida. Se usa tras dar de alta una localidad con Ctrl+L:
        este widget vive dentro de dialogos que se ocultan y se reutilizan, asi
        que su listado se quedaba con los datos del arranque y la localidad
        nueva no aparecia hasta reiniciar."""
        curr = _get_curr()
        it = self.country_combo.get_active_iter()
        if it is None:
            return
        code = self.country_combo.get_model().get_value(it, 1)

        # recordar la localidad seleccionada para no perderla al recargar
        sel_city = None
        model, sit = self.locview.get_selection().get_selected()
        if sit is not None:
            sel_city = model.get_value(sit, 0)

        liststore = Gtk.ListStore(str, str, str)
        i = 0
        for n, c in enumerate(curr.datab.fetch_all_from_country(code, curr.usa)):
            liststore.append(c)
            if sel_city is not None and c[0] == sel_city:
                i = n
        self.locmodel = liststore

        # _recargando evita que on_sel_changed recalcule la carta al restaurar
        # la seleccion (seria un efecto colateral de refrescar una lista).
        self._recargando = True
        try:
            if self.filtcheck.get_active() and hasattr(self, 'reg_code'):
                filtmodel = self.locmodel.filter_new()
                filtmodel.set_visible_func(filter_region, self.reg_code)
                self.locview.set_model(filtmodel)
            else:
                self.locview.set_model(liststore)
                if sel_city is not None:
                    path = Gtk.TreePath.new_from_indices([i])
                    self.locview.set_cursor(path)
                    self.locview.scroll_to_cell(path)
        finally:
            self._recargando = False

    def on_reg_selected(self, combo):
        model = combo.get_model()
        active = combo.get_active()
        if active < 0:
            return
        self.reg_code = model[active][1]
        if self.filtcheck.get_active():
            filtmodel = self.locmodel.filter_new()
            filtmodel.set_visible_func(filter_region, self.reg_code)
            self.locview.set_model(filtmodel)

    def on_count_selected(self, combo):
        it = combo.get_active_iter()
        if not it:
            return
        curr = _get_curr()
        model = combo.get_model()
        code = model.get_value(it, 1)
        liststore = Gtk.ListStore(str, str)
        rlist = curr.datab.list_regions(code, curr.usa)
        for r in rlist:
            liststore.append(r)
        self.reg_combo.set_model(liststore)
        self.reg_combo.set_active(0)
        liststore = Gtk.ListStore(str, str, str)
        loclist = curr.datab.fetch_all_from_country(code, curr.usa)
        for c in loclist:
            liststore.append(c)
        self.locview.set_model(liststore)
        self.locmodel = liststore
        self.set_country_code(code)

    def set_country_code(self, code):
        _get_curr().country = code

    def on_count_match(self, compl, model, it):
        sel = model.get_value(it, 0)
        for r in self.country_combo.get_model():
            if r[0] == sel:
                self.country_combo.set_active_iter(r.iter)
                break

    def on_usa_toggled(self, check, cpl, lbl):
        boss = _get_boss()
        curr = _get_curr()
        if check.get_active():
            curr.usa = True
            lbl.set_text(_("Estado"))
        else:
            curr.usa = False
            lbl.set_text(_("Pais"))
        self.countries = curr.datab.get_states_tuple(curr.usa)
        self.sortlist = sorted(self.countries)
        model = Gtk.ListStore(str, str)
        for n, c in self.sortlist:
            model.append([n, c])
        self.country_combo.set_model(model)
        cpl.set_model(model)
        for r in model:
            if r[1] == boss.opts.country:
                self.country_combo.set_active_iter(r.iter)
                break
        else:
            self.country_combo.set_active(0)

    def on_filter_toggled(self, check):
        if check.get_active():
            filtmodel = self.locmodel.filter_new()
            filtmodel.set_visible_func(filter_region, self.reg_code)
            self.locview.set_model(filtmodel)
        else:
            self.locview.set_model(self.locmodel)
        self.locview.get_selection().select_path("0")

    def on_row_activate(self, tree, path, col):
        model, it = tree.get_selection().get_selected()
        city, code = model.get(it, 0, 1)
        self.actualize_if_needed(city, code)

    def on_sel_changed(self, sel):
        if getattr(self, '_recargando', False):
            return          # refresco del listado, no una eleccion del usuario
        model, it = sel.get_selected()
        if not it:
            return
        city, code = model.get(it, 0, 1)
        for r in self.reg_combo.get_model():
            if code == r[1]:
                self.reg_combo.set_active_iter(r.iter)
                break
        self.actualize_if_needed(city, code)

    def actualize_if_needed(self, city, code):
        boss = _get_boss()
        curr = _get_curr()
        curr.setloc(city, code)
        if curr.curr_chart == curr.now:
            curr.set_now()
        if curr.curr_op == 'draw_local' or boss.mainwin.locselflag:
            boss.da.redraw()
        else:
            active = boss.mpanel.active_slot
            curr.setchart()
            curr.act_pool(active, curr.calc)

    def set_default_local(self):
        boss = _get_boss()
        curr = _get_curr()
        usa = {'false': False, 'true': True}[boss.opts.usa]
        if usa != self.check.get_active():
            self.check.set_active(usa)
            return
        self.countries = curr.datab.get_states_tuple(usa)
        self.sortlist = sorted(self.countries)
        model = Gtk.ListStore(str, str)
        for n, c in self.sortlist:
            model.append([n, c])
        self.country_combo.set_model(model)

        for r in model:
            if r[1] == boss.opts.country:
                self.country_combo.set_active_iter(r.iter)
                break
        else:
            self.country_combo.set_active(0)

        liststore = Gtk.ListStore(str, str, str)
        loclist = curr.datab.fetch_all_from_country(boss.opts.country, usa)
        i = 0
        for n, c in enumerate(loclist):
            liststore.append(c)
            if boss.opts.locality == c[0]:
                i = n
        self.locview.set_model(liststore)
        self.locmodel = liststore
        self.locview.set_cursor(Gtk.TreePath.new_from_indices([i]))
        self.locview.scroll_to_cell(Gtk.TreePath.new_from_indices([i]))
