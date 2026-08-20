# -*- coding: utf-8 -*-
import re

from gi.repository import Gtk

from astronex.extensions.path import path
from astronex.extensions.validation import MaskEntry
from astronex.utils import degtodec
from astronex.countries import cata_reg


def _boss():
    from astronex.boss import boss
    return boss


def _curr():
    return _boss().get_state()


def _datab():
    return _boss().get_database()


def _combo_text(combo):
    it = combo.get_active_iter()
    if it is not None:
        return combo.get_model()[it][0]
    child = combo.get_child()
    if child is not None:
        return child.get_text()
    return ""


class CustomLocDlg(Gtk.Dialog):
    def __init__(self, boss, parent=None):
        # transient_for=parent: como el resto de dialogos (EntryDlg, ConfigDlg).
        # Sin destroy_with_parent: el dialogo se oculta y se reutiliza
        # (winnex.customloc_dlg), nunca se destruye (evita el segfault GTK3/WSLg).
        Gtk.Dialog.__init__(self,
                            title=_("Anadir localidad"),
                            parent=parent,
                            modal=True)
        self.add_buttons(_("_Guardar"), Gtk.ResponseType.OK,
                         _("_Cerrar"), Gtk.ResponseType.NONE)
        self.set_size_request(400, 500)

        self.locwidget = CustomLocWidget(self)
        frame = Gtk.Frame()
        frame.add(self.locwidget)
        content = self.get_content_area()
        content.pack_start(frame, False, False, 0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        but = Gtk.Button(label=_('Eliminar entrada'))
        but.connect('clicked', self.on_delete_entry)
        hbox.pack_start(but, False, False, 0)
        but = Gtk.Button(label=_('Modificar entrada'))
        but.connect('clicked', self.on_modify_entry)
        hbox.pack_end(but, False, False, 0)
        content.pack_start(hbox, False, False, 0)
        content.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        view = self.make_browser()
        sw.add(view)
        self.locview = view
        content.pack_start(sw, True, True, 0)

        # ESC/X o el boton _Cerrar OCULTAN el dialogo (no lo destruyen) y se
        # reutiliza luego. Destruir este dialogo con ESC en GTK3/WSLg provocaba
        # un segfault que mataba toda la app; al no destruirlo NUNCA durante la
        # sesion se evita por completo el camino de finalizacion que crasheaba.
        # El dialogo se crea una vez (winnex.customloc_dlg) y se vuelve a
        # mostrar con Ctrl-L. (Mismo patron aprobado en HelpWindow.)
        self.connect("response", self.dlg_response)
        self.connect("delete-event", self.on_delete)
        self.set_response_sensitive(Gtk.ResponseType.OK, False)
        self.show_all()

    def dlg_response(self, dialog, rid):
        if rid == Gtk.ResponseType.OK:
            resp = self.locwidget.pack_response()
            _datab().save_attached_loc(resp)
            locmodel = Gtk.ListStore(str, str, str, str, str)
            loclist = _datab().fetch_all_from_custom()
            for c in loclist:
                locmodel.append(c)
            self.locview.set_model(locmodel)
            # Refrescar los listados de localidades ya abiertos. El dialogo de
            # Entradas (y el selector Ctrl+N) construyen su lista una sola vez y
            # se reutilizan durante toda la sesion, asi que sin esto la
            # localidad recien creada no aparecia entre las localidades hasta
            # reiniciar el programa: era lo que reportaba Elias ("meto los datos
            # y despues no aparece entre las localidades").
            from astronex.gui.localwidget import reload_all_localities
            reload_all_localities()
        else:
            # No destruir: ocultar. ESC y el boton _Cerrar (ResponseType.NONE)
            # llegan aqui; al ocultar en vez de destruir se evita el segfault.
            self.hide()

    def on_delete(self, widget, event):
        # No destruir: ocultar (return True evita el destroy por defecto).
        self.hide()
        return True

    def on_delete_entry(self, but):
        model, it = self.locview.get_selection().get_selected()
        if not it:
            return
        result = self.deletedialog()
        if result == Gtk.ResponseType.OK:
            city = model.get_value(it, 0)
            code = model.get_value(it, 1)
            table = model.get_value(it, 3)
            _datab().delete_custom_loc(table, city, code)
            locmodel = Gtk.ListStore(str, str, str, str, str)
            loclist = _datab().fetch_all_from_custom()
            for c in loclist:
                locmodel.append(c)
            self.locview.set_model(locmodel)

    def deletedialog(self):
        msg = [_("Eliminar una localidad puede impedir modificar "),
               _("luego una carta con facilidad. Continuar?")]
        dialog = Gtk.MessageDialog(transient_for=None, modal=True,
                                   message_type=Gtk.MessageType.WARNING,
                                   buttons=Gtk.ButtonsType.OK_CANCEL,
                                   text="\n".join(msg))
        result = dialog.run()
        dialog.hide()  # no destruir toplevel (segfault GTK3/WSLg); ocultar
        return result

    def on_modify_entry(self, but):
        model, it = self.locview.get_selection().get_selected()
        if not it:
            return
        city = model.get_value(it, 0)
        code = model.get_value(it, 1)
        geo = model.get_value(it, 2)
        table = model.get_value(it, 3)
        count = model.get_value(it, 4)
        self.locwidget.locentry.set_text(city)
        self.locwidget.country_combo.get_child().set_text(count)
        lng, lat = geo.split(' ')
        d, L, m = lng.partition('E')
        if L == '':
            d, L, m = lng.partition('W')
        self.locwidget.gcombos[0].set_active(['E', 'W'].index(L))
        self.locwidget.gentries[0].set_text(".".join([d.rjust(3, '0'), m, '00']))
        d, L, m = lat.partition('N')
        if L == '':
            d, L, m = lat.partition('S')
        self.locwidget.gcombos[1].set_active(['N', 'S'].index(L))
        self.locwidget.gentries[1].set_text(".".join([d, m, '00']))
        _, count_code = table.split('_')
        if count_code.startswith('US'):
            self.locwidget.check.set_active(True)
            reg = _datab().get_usadistrict_from_code(count_code[2:], code)
        else:
            self.locwidget.check.set_active(False)
            reg = _datab().get_regionname_from_code(count_code.upper(), code)
        model2 = self.locwidget.reg_combo.get_model()
        for r in model2:
            if r[0] == reg:
                self.locwidget.reg_combo.set_active_iter(r.iter)
                break

    def make_browser(self):
        locmodel = Gtk.ListStore(str, str, str, str, str)
        locview = Gtk.TreeView(model=locmodel)
        selection = locview.get_selection()
        selection.set_mode(Gtk.SelectionMode.SINGLE)
        loclist = _datab().fetch_all_from_custom()
        for c in loclist:
            locmodel.append(c)

        cell = Gtk.CellRendererText()
        cell.set_property('width-chars', 26)
        from astronex.gui.mainnb import _is_dark_theme
        cell.set_property('foreground', '#7eb6ff' if _is_dark_theme() else 'blue')
        cellgeo = Gtk.CellRendererText()
        cellcount = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn()
        column.pack_start(cell, False)
        column.pack_start(cellgeo, False)
        column.pack_start(cellcount, False)
        column.set_attributes(cell, text=0)
        column.set_attributes(cellgeo, text=2)
        column.set_attributes(cellcount, text=4)
        column.set_widget(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        locview.append_column(column)
        locview.set_headers_visible(False)
        return locview


def filter_region(model, it, code):
    value = model.get_value(it, 1)
    return value == code


class CustomLocWidget(Gtk.Box):
    def __init__(self, dialog):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self.set_homogeneous(False)
        self.dialog = dialog
        self.usa = False
        boss = _boss()
        curr = _curr()
        datab = _datab()

        self.countries = datab.get_states()
        self.countrycode = curr.country
        compl = Gtk.EntryCompletion()

        region = curr.loc.region
        self.locmodel = None
        self.locname = ""

        self.sortlist = sorted(self.countries.keys())
        revlist = dict((reversed(list(i)) for i in self.countries.items()))
        default = self.sortlist.index(revlist[self.countrycode])

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.set_border_width(4)
        label1 = Gtk.Label(label=_('Pais') + "      ")
        label2 = Gtk.Label(label=_('Region'))
        hbox.pack_start(label1, False, False, 8)
        self.check = Gtk.CheckButton(label="Usa")
        self.check.connect('toggled', self.on_usa_toggled, compl, default, label1)
        hbox.pack_start(self.check, False, False, 0)
        hbox.pack_end(label2, False, False, 8)
        self.pack_start(hbox, False, False, 0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.set_border_width(6)
        liststore = Gtk.ListStore(str)
        self.country_combo = Gtk.ComboBox.new_with_model_and_entry(liststore)
        self.country_combo.set_entry_text_column(0)

        for c in self.sortlist:
            liststore.append([c])

        compl.set_text_column(0)
        compl.set_model(self.country_combo.get_model())
        entry = self.country_combo.get_child()
        entry.set_completion(compl)
        compl.connect('match-selected', self.on_count_match)

        self.country_combo.set_active(default)
        self.country_combo.set_wrap_width(4)
        self.country_combo.connect('changed', self.on_count_selected)

        hbox.pack_start(self.country_combo, False, False, 0)

        liststore = Gtk.ListStore(str, str)
        self.reg_combo = Gtk.ComboBox.new_with_model_and_entry(liststore)
        self.reg_combo.set_entry_text_column(0)
        self.reg_combo.connect('changed', self.on_reg_selected)
        rlist = datab.list_regions(self.countrycode)
        if self.countrycode == "SP" and boss.opts.lang == 'ca':
            rlist = [(cata_reg[r[0]], r[1]) for r in rlist]

        i = 0
        for n, r in enumerate(rlist):
            liststore.append(r)
            if region == r[0]:
                i = n

        self.reg_combo.set_active(i)
        hbox.pack_end(self.reg_combo, False, False, 0)
        self.pack_start(hbox, False, False, 0)

        table = Gtk.Table(n_rows=3, n_columns=3)
        table.set_border_width(6)
        table.set_col_spacings(6)
        for row, lbl_text in enumerate([_("Localidad"), _("Longitud"), _("Latitud")]):
            label = Gtk.Label(label=lbl_text)
            label.set_alignment(1.0, 0.5)
            table.attach(label, 0, 1, row, row + 1)

        locname = Gtk.Entry()
        table.attach(locname, 1, 3, 0, 1)
        locname.connect('changed', self.on_locname_changed)
        self.locentry = locname

        self.gentries = []
        self.longdeg = "0"
        lng = MaskEntry()
        lng.set_mask("000.00.00")
        lng.set_width_chars(len(lng.get_mask()))
        lng.set_text("000.00.00")
        lng.connect("changed", self.on_geoentry_changed, 'long')
        table.attach(lng, 1, 2, 1, 2)
        self.gentries.append(lng)

        self.gcombos = []
        store = Gtk.ListStore(str)
        store.append([_('E')])
        store.append([_('W')])
        combo = Gtk.ComboBox.new_with_model(store)
        cell = Gtk.CellRendererText()
        combo.pack_start(cell, True)
        combo.add_attribute(cell, 'text', 0)
        combo.set_size_request(40, -1)
        combo.connect('changed', self.on_geocombo_changed, 'long')
        combo.set_active(0)
        self.longletter = 'E'
        table.attach(combo, 2, 3, 1, 2)
        self.gcombos.append(combo)

        self.latdeg = "0"
        lat = MaskEntry()
        lat.set_mask("00.00.00")
        lat.set_width_chars(len(lat.get_mask()))
        lat.set_text("00.00.00")
        lat.connect("changed", self.on_geoentry_changed, 'lat')
        table.attach(lat, 1, 2, 2, 3)
        self.gentries.append(lat)

        store = Gtk.ListStore(str)
        store.append([_('N')])
        store.append([_('S')])
        combo = Gtk.ComboBox.new_with_model(store)
        cell = Gtk.CellRendererText()
        combo.pack_start(cell, True)
        combo.add_attribute(cell, 'text', 0)
        combo.set_size_request(40, -1)
        combo.connect('changed', self.on_geocombo_changed, 'lat')
        combo.set_active(0)
        self.latletter = 'N'
        table.attach(combo, 2, 3, 2, 3)
        self.gcombos.append(combo)

        self.pack_start(table, False, False, 0)

    def on_reg_selected(self, combo):
        model = combo.get_model()
        active = combo.get_active()
        if active < 0:
            return
        self.reg_code = model[active][1]

    def on_count_selected(self, combo):
        sel = _combo_text(combo)
        try:
            code = self.countries[sel]
            liststore = Gtk.ListStore(str, str)
            rlist = _datab().list_regions(code, self.usa)
            for r in rlist:
                liststore.append(r)
            self.reg_combo.set_model(liststore)
            self.reg_combo.set_active(0)
            self.set_country_code(code)
        except KeyError:
            pass

    def set_country_code(self, code):
        self.countrycode = code

    def on_count_match(self, compl, model, it):
        sel = model.get_value(it, 0)
        sl = self.sortlist
        if sel in sl:
            self.country_combo.set_active(sl.index(sel))

    def on_usa_toggled(self, check, cpl, dfl, lbl):
        datab = _datab()
        if check.get_active():
            self.usa = True
            self.countries = datab.get_states(True)
            default = 0
            lbl.set_text(_("Estado"))
        else:
            self.usa = False
            self.countries = datab.get_states()
            default = dfl
            lbl.set_text(_("Pais"))
        self.sortlist = sorted(self.countries.keys())
        model = Gtk.ListStore(str)
        for c in self.sortlist:
            model.append([c])
        self.country_combo.set_model(model)
        cpl.set_model(model)
        self.country_combo.set_active(default)

    def on_geocombo_changed(self, combo, geo):
        if geo == 'long':
            self.longletter = ['E', 'W'][combo.get_active()]
        else:
            self.latletter = ['N', 'S'][combo.get_active()]

    def on_geoentry_changed(self, entry, geo):
        fields = entry.get_field_text()
        if None in fields:
            return

        def pad(f, i):
            n = 3 if (i == 0 and geo == 'long') else 2
            return str(f).rjust(n, '0')

        mayor = {'long': 180, 'lat': 80}
        checks = [mayor[geo], 60, 60]
        for i, fld in enumerate(fields):
            if fld and fld >= checks[i]:
                fields[i] = 0
                wrongdeg = '.'.join((pad(f, j) for j, f in enumerate(fields)))
                entry.set_text(wrongdeg)

        if geo == "long":
            longdeg = ''.join((pad(f, i) for i, f in enumerate(fields)))
            self.longdeg = longdeg[:-1].lstrip('0') + longdeg[-1]
        else:
            latdeg = ''.join((pad(f, i) for i, f in enumerate(fields)))
            self.latdeg = latdeg[:-1].lstrip('0') + latdeg[-1]

    def on_locname_changed(self, entry):
        locname = entry.get_text()
        if not re.match(r"^\w(\w|-\s)*", locname, re.U):
            self.dialog.set_response_sensitive(Gtk.ResponseType.OK, False)
            entry.set_text("")
        else:
            self.locname = locname
            self.dialog.set_response_sensitive(Gtk.ResponseType.OK, True)

    def pack_response(self):
        if self.locname == "":
            return None
        if self.longletter == 'W' and self.longdeg != '0':
            self.longdeg = "-" + self.longdeg
        if self.latletter == 'S' and self.latdeg != '0':
            self.latdeg = "-" + self.latdeg
        if self.usa:
            longdeg = degtodec(self.longdeg)
            latdeg = degtodec(self.latdeg)
        else:
            longdeg = self.longdeg
            latdeg = self.latdeg
        return self.countrycode, self.reg_code, self.locname, latdeg, longdeg, self.usa
