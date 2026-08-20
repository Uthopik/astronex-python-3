# -*- coding: utf-8 -*-
from gi.repository import Gtk, Gdk, Pango

from configobj import ConfigObj

from astronex.extensions.path import path
from astronex.gui.localwidget import LocWidget
from astronex.gui.searchview import SearchView


def _boss():
    from astronex.boss import boss
    return boss


def _curr():
    return _boss().get_state()


MARKUP = "<b><i>%s</i></b>"
elem = ["fire", "earth", "air", "water"]
plan = ["pers", "trans", "tool", "node"]
asp = ["orange", "red", "blue", "green"]
aux = ['click1', 'click2', 'inv', 'low', 'transcol']


def _rgba_to_hex_pair(rgba):
    """Convierte Gdk.RGBA (0.0-1.0) a (hex_with_hash, hex_no_hash) en formato rrrrggggbbbb (GTK2 16-bit)."""
    r = int(rgba.red * 65535)
    g = int(rgba.green * 65535)
    b = int(rgba.blue * 65535)
    hex_str = "%04x%04x%04x" % (r, g, b)
    return '#' + hex_str, hex_str


def _hex_to_rgba(hex_str):
    """Acepta '#rrrrggggbbbb' (GTK2 16-bit) o '#rrggbb' (8-bit). Retorna Gdk.RGBA."""
    s = hex_str.lstrip('#')
    rgba = Gdk.RGBA()
    if len(s) == 12:
        r = int(s[0:4], 16) / 65535.0
        g = int(s[4:8], 16) / 65535.0
        b = int(s[8:12], 16) / 65535.0
        rgba.red, rgba.green, rgba.blue, rgba.alpha = r, g, b, 1.0
    else:
        rgba.parse('#' + s)
    return rgba


class ConfigDlg(Gtk.Dialog):
    '''Property dialog'''
    groups = [_("Localidad"), _("Tablas"), _("Colores"),
              _("Lineas"), _("Fuentes"), _("Orbes"), _("Lenguage"), _("PNG")]

    def __init__(self, parent):
        boss = _boss()
        opts = boss.opts
        self.config_file = path.joinpath(boss.home_dir, boss.config_file)

        Gtk.Dialog.__init__(self,
                            title=_("Configuracion"),
                            transient_for=parent)
        # NO usar destroy_with_parent: en WSLg/GTK3 destruir este dialogo (con
        # ESC, la X o al cerrar la app) recorria un camino de finalizacion que
        # provocaba un segfault. Igual que HelpWindow, el dialogo se OCULTA y se
        # REUTILIZA (winnex.config), nunca se destruye durante la sesion.
        self.add_button(_("_Cerrar"), Gtk.ResponseType.NONE)
        self.add_button(_("_Guardar"), Gtk.ResponseType.OK)
        self.set_size_request(550, 380)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.set_border_width(3)
        hbox.pack_start(self.index_table(), False, False, 0)
        hbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)

        self.notebook = Gtk.Notebook()
        self.notebook.set_show_tabs(False)
        self.notebook.set_show_border(True)

        widget = ConfLocWidget()
        self.notebook.append_page(self.build_nbpage(widget, _("Localidad por defecto")))

        widget = TablesPage(boss.datab)
        self.notebook.append_page(self.build_nbpage(widget, _("Tablas por defecto")))

        widget = ColorsPage()
        self.notebook.append_page(self.build_nbpage(widget, _("Colores")))

        widget = LinesPage()
        self.notebook.append_page(self.build_nbpage(widget, _("Lineas")))

        widget = FontsPage()
        self.notebook.append_page(self.build_nbpage(widget, _("Fuentes")))

        widget = OrbsPage()
        self.notebook.append_page(self.build_nbpage(widget, _("Orbes")))

        widget = LangPage()
        self.notebook.append_page(self.build_nbpage(widget, _("Lenguage por defecto")))

        widget = PngPage()
        self.notebook.append_page(self.build_nbpage(widget, _("Tamano de imagen PNG")))

        hbox.pack_start(self.notebook, True, True, 0)
        self.get_content_area().pack_start(hbox, True, True, 0)
        self.connect("response", self.dlg_response)
        # La X (delete-event) OCULTA en vez de destruir (return True). ESC ya se
        # canaliza por la senal 'response' (DELETE_EVENT) -> dlg_response, que
        # tambien oculta. Asi el dialogo nunca se destruye -> no hay segfault.
        self.connect("delete-event", self.on_delete)
        self.show_all()

        wpos = self.get_position()
        self.pos_x = wpos[0]
        self.pos_y = wpos[1]

    def dlg_response(self, dialog, rid):
        if rid == Gtk.ResponseType.OK:
            boss = _boss()
            conf = ConfigObj(str(self.config_file), encoding='utf-8')
            boss.opts.opts_to_config(conf)
            conf.write()
        # Ocultar (no destruir): el dialogo se reutiliza con show_all()+present()
        # desde winnex.on_props_clicked. Destruirlo aqui crasheaba en WSLg/GTK3.
        dialog.hide()

    def on_delete(self, widget, event):
        # La X oculta la ventana; return True evita el destroy por defecto.
        self.hide()
        return True

    def index_table(self):
        model = Gtk.ListStore(str)
        view = SearchView(model)
        view.set_size_request(100, -1)
        view.set_rules_hint(True)
        selection = view.get_selection()
        selection.set_mode(Gtk.SelectionMode.SINGLE)
        for o in self.groups:
            model.append((o,))
        cell = Gtk.CellRendererText()
        cell.weight = 600
        column = Gtk.TreeViewColumn(None, cell, text=0)
        view.append_column(column)
        view.set_headers_visible(False)
        view.set_enable_search(False)
        sel = view.get_selection()
        sel.set_mode(Gtk.SelectionMode.SINGLE)
        sel.connect('changed', self.on_sel_changed)
        return view

    def on_sel_changed(self, sel):
        model, it = sel.get_selected()
        if it is None:
            return
        index = model.get_path(it)[0]
        self.notebook.set_current_page(index)

    def build_nbpage(self, widget, text):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        label = Gtk.Label()
        label.set_markup(MARKUP % text)
        vbox.pack_start(label, False, False, 0)
        vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)
        vbox.pack_start(widget, True, True, 0)
        return vbox


class ConfLocWidget(LocWidget):
    def __init__(self):
        LocWidget.__init__(self, default=True)
        self.country_combo.set_size_request(-1, -1)
        self.reg_combo.set_size_request(-1, -1)

    def on_row_activate(self, tree, path, col):
        return

    def actualize_if_needed(self, city, code):
        boss = _boss()
        curr = _curr()
        curr.setloc(city, code)
        boss.opts.locality = city
        boss.opts.region = code

    def set_country_code(self, code):
        boss = _boss()
        curr = _curr()
        curr.country = code
        boss.opts.country = code

    def on_usa_toggled(self, check, cpl, lbl):
        LocWidget.on_usa_toggled(self, check, cpl, lbl)
        usa = ['false', 'true'][int(check.get_active())]
        _boss().opts.usa = usa


def _combo_active_text(combo):
    it = combo.get_active_iter()
    if it is not None:
        return combo.get_model()[it][0]
    child = combo.get_child()
    if child is not None:
        return child.get_text()
    return ""


class TablesPage(Gtk.Box):
    def __init__(self, datab):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self.set_border_width(6)
        boss = _boss()
        curr = _curr()

        wtab = Gtk.Table(n_rows=3, n_columns=2)
        wtab.set_row_spacings(6)
        wtab.set_col_spacings(6)
        wtab.set_homogeneous(False)
        label = Gtk.Label(label=_('Inicio: '))
        liststore, index = self.get_table_list(datab, boss.opts.database)
        table = Gtk.ComboBox.new_with_model_and_entry(liststore)
        table.set_entry_text_column(0)
        table.get_child().set_editable(False)
        table.connect('changed', self.on_tables_changed)
        table.set_active(index)
        hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hb.pack_end(label, False, False, 0)
        wtab.attach(hb, 0, 1, 0, 1)
        wtab.attach(table, 1, 2, 0, 1)

        label = Gtk.Label(label=_('Favoritos: '))
        liststore, index = self.get_table_list(datab, boss.opts.favourites)
        table = Gtk.ComboBox.new_with_model_and_entry(liststore)
        table.set_entry_text_column(0)
        table.get_child().set_editable(False)
        table.connect('changed', self.on_fav_changed)
        if index > -1:
            table.set_active(index)

        hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hb.pack_end(label, False, False, 0)
        wtab.attach(hb, 0, 1, 1, 2)
        wtab.attach(table, 1, 2, 1, 2)

        label = Gtk.Label(label=_('N. favoritos: '))
        nfav = int(boss.opts.nfav)
        adj = Gtk.Adjustment(value=nfav, lower=1, upper=10, step_increment=1, page_increment=1, page_size=0)
        spin = Gtk.SpinButton()
        spin.set_adjustment(adj)
        spin.set_alignment(1.0)
        spin.connect('value-changed', self.on_spin_changed)
        hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hb.pack_end(label, False, False, 0)
        wtab.attach(hb, 0, 1, 2, 3)
        wtab.attach(spin, 1, 2, 2, 3, xpadding=60)

        align = Gtk.Alignment(xalign=0.5, yalign=0.5)
        align.add(wtab)
        self.pack_start(align, False, False, 0)

    def get_table_list(self, datab, default):
        liststore = Gtk.ListStore(str)
        tablelist = datab.get_databases()
        for c in tablelist:
            liststore.append([c])
        index = -1
        for i, r in enumerate(liststore):
            if r[0] == default:
                index = i
                break
        return liststore, index

    def on_tables_changed(self, combo):
        _boss().opts.database = _combo_active_text(combo)

    def on_fav_changed(self, combo):
        boss = _boss()
        curr = _curr()
        tbl = _combo_active_text(combo)
        boss.opts.favourites = tbl
        nfav = int(boss.opts.nfav)
        curr.fav = curr.datab.get_favlist(tbl, nfav, curr.newchart())

    def on_spin_changed(self, spin):
        boss = _boss()
        curr = _curr()
        value = spin.get_value_as_int()
        boss.opts.nfav = value
        tbl = boss.opts.favourites
        curr.fav = curr.datab.get_favlist(tbl, value, curr.newchart())


class ColorsPage(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self.set_border_width(6)
        boss = _boss()
        cols = boss.get_colors()

        table = Gtk.Table(n_rows=6, n_columns=4)
        labels = [(_("Fuego"), 'fire'), (_("Tierra"), 'earth'),
                  (_("Aire"), 'air'), (_("Agua"), 'water'),
                  (_("Pers."), 'pers'), (_("Herr."), 'tool'),
                  (_("Trans."), 'trans'), (_("Nodo"), 'node'),
                  (_("Conj."), 'orange'), (_("Rojo"), 'red'),
                  (_("Azul"), 'blue'), (_("Verde"), 'green')]

        self.make_table(table, labels, 4, cols)
        table.set_col_spacing(1, 3)
        table.set_col_spacing(3, 3)
        table.set_row_spacing(3, 6)
        self.pack_start(table, False, False, 0)

        table = Gtk.Table(n_rows=4, n_columns=3)
        labels = [(_("Primera pers."), 'click1'), (_("Segunda pers."), 'click2'),
                  (_("P. Inversion"), 'inv'), (_("P. Reposo"), 'low')]
        self.make_table(table, labels, 2, cols)

        lbl = Gtk.Label(label=_('Transitos'))
        lbl.set_alignment(0.0, 0.5)
        colbut = Gtk.ColorButton()
        colbut.set_rgba(_hex_to_rgba(cols['transcol']))
        colbut.label = 'transcol'
        colbut.connect('color-set', self.color_set_cb, 'transcol')
        table.attach(lbl, 0, 1, 3, 4)
        table.attach(colbut, 1, 2, 3, 4)
        table.set_col_spacings(10)
        self.pack_start(table, False, False, 0)

        # Toggle modo oscuro
        darkbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        darkbox.set_border_width(6)
        self.darkbut = Gtk.CheckButton(label=_("Modo oscuro (requiere reiniciar)"))
        is_dark = str(getattr(boss.opts, 'darkmode', 'false')).lower() in ('true', '1', 'yes')
        self.darkbut.set_active(is_dark)
        self.darkbut.connect('toggled', self.on_dark_toggled)
        darkbox.pack_start(self.darkbut, False, False, 0)
        self.pack_start(darkbox, False, False, 0)

        buttbox = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL)
        buttbox.set_layout(Gtk.ButtonBoxStyle.END)
        button = Gtk.Button(label=_("Restablecer"))
        button.connect('clicked', self.color_reset)
        buttbox.pack_start(button, False, False, 0)
        self.pack_end(buttbox, False, False, 0)

    def on_dark_toggled(self, but):
        boss = _boss()
        boss.opts.darkmode = 'true' if but.get_active() else 'false'

    def make_table(self, table, labels, ix, cols):
        for i in range(len(labels)):
            lbl = Gtk.Label(label=labels[i][0])
            lbl.set_alignment(0.0, 0.5)
            colbut = Gtk.ColorButton()
            colbut.set_rgba(_hex_to_rgba(cols[labels[i][1]]))
            colbut.label = labels[i][1]
            colbut.connect('color-set', self.color_set_cb, labels[i][1])
            r = i % ix
            cc = (i // ix) * 2
            table.attach(lbl, cc, cc + 1, r, r + 1)
            table.attach(colbut, cc + 1, cc + 2, r, r + 1)

    def color_set_cb(self, colbut, lbl):
        boss = _boss()
        rgba = colbut.get_rgba()
        hex_with, hex_no = _rgba_to_hex_pair(rgba)
        cols = boss.get_colors()
        cols[lbl] = hex_with
        setattr(boss.opts, lbl, hex_no)
        if lbl in elem:
            boss.opts.zodiac.set_zodcolors()
        elif lbl in plan:
            boss.opts.zodiac.set_plancolors()
        elif lbl in asp:
            boss.opts.zodiac.set_aspcolors()
        elif lbl in aux:
            boss.opts.zodiac.set_auxcolors()
        boss.redraw()

    def color_reset(self, but):
        boss = _boss()
        boss.reset_colors()
        boss.opts.zodiac.set_allcolors()
        boss.redraw()
        cols = boss.get_colors()
        for ch0 in self.get_children():
            if hasattr(ch0, 'get_children'):
                for ch1 in ch0.get_children():
                    if isinstance(ch1, Gtk.ColorButton):
                        lbl = getattr(ch1, 'label', None)
                        if lbl:
                            ch1.set_rgba(_hex_to_rgba(cols[lbl]))


class LinesPage(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self.set_border_width(6)
        boss = _boss()

        buttbox = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL)
        buttbox.set_layout(Gtk.ButtonBoxStyle.EDGE)
        label = Gtk.Label(label=_("Base"))
        buttbox.pack_start(label, True, True, 0)
        base = float(boss.opts.base)
        adj = Gtk.Adjustment(value=base, lower=0.2, upper=2.4,
                             step_increment=0.05, page_increment=0.1, page_size=0)
        spin = Gtk.SpinButton()
        spin.set_adjustment(adj)
        spin.set_digits(2)
        spin.connect('value-changed', self.line_set_cb)
        buttbox.pack_start(spin, True, True, 0)
        self.pack_start(buttbox, False, False, 0)

    def line_set_cb(self, spin):
        boss = _boss()
        value = spin.get_value()
        boss.opts.base = value
        boss.redraw()


class FontsPage(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self.set_border_width(6)
        self.set_spacing(8)
        boss = _boss()

        buttbox = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL)
        buttbox.set_layout(Gtk.ButtonBoxStyle.SPREAD)
        fontbutton = Gtk.FontButton.new_with_font(boss.opts.font)
        fontbutton.set_use_font(True)
        fontbutton.set_title(_("Elige una fuente"))
        fontbutton.connect('font-set', self.font_set_cb)
        buttbox.pack_start(fontbutton, True, True, 0)
        self.pack_start(buttbox, False, True, 0)

        font = Pango.FontDescription.from_string("Astro-Nex")
        buttbox = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL)
        buttbox.set_layout(Gtk.ButtonBoxStyle.SPREAD)
        store = Gtk.ListStore(str)
        store.append([' z c '])
        store.append([' Z C '])
        combo = Gtk.ComboBox.new_with_model(store)
        combo.set_border_width(3)
        cell = Gtk.CellRendererText()
        cell.set_property('font-desc', font)
        cell.set_property('alignment', Pango.Alignment.RIGHT)
        combo.pack_start(cell, True)
        combo.add_attribute(cell, 'text', 0)
        combo.connect('changed', self.style_set_cb)
        style = [0, 1][boss.opts.transtyle == 'classic']
        combo.set_active(style)
        buttbox.pack_start(combo, False, True, 0)
        self.pack_start(buttbox, False, False, 0)

    def font_set_cb(self, fontbutton):
        boss = _boss()
        font = fontbutton.get_font_name() if hasattr(fontbutton, 'get_font_name') else fontbutton.get_font()
        boss.opts.font = font
        boss.redraw()

    def style_set_cb(self, combo):
        boss = _boss()
        s = ['huber', 'classic'][combo.get_active()]
        if s != boss.opts.transtyle:
            boss.opts.transtyle = s
            boss.opts.zodiac.swap_plan_style()
            zodiac = boss.opts.zodiac.__class__
            boss.da.drawer.planetmanager.glyphs = zodiac.plan[:]
            boss.da.redraw()


class OrbsPage(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self.set_border_width(6)
        boss = _boss()
        font = Pango.FontDescription.from_string("Astro-Nex")

        # Un solo Gtk.Grid: columna de planetas + separador + columnas de orbes.
        # Filas homogeneas => glifos de planeta alineados con sus valores.
        grid = Gtk.Grid()
        grid.set_border_width(12)
        grid.set_row_spacing(12)
        grid.set_column_spacing(16)
        grid.set_row_homogeneous(True)

        # Columna 0: glifos de planetas por categoria (cabecera vacia + 4 grupos)
        planet_labs = ['', 'd,f', 'h,j,l', 'k,g', 'z,x,c']
        for i, l in enumerate(planet_labs):
            lbl = Gtk.Label(label=l)
            lbl.override_font(font)
            lbl.set_halign(Gtk.Align.CENTER)
            grid.attach(lbl, 0, i, 1, 1)

        # Columna 1: separador vertical entre planetas y valores
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        grid.attach(sep, 1, 0, 1, 5)

        # Columnas 2-6: cabecera de aspectos (glifos) + 4 filas de orbes
        head = ['2', '36', '4', '5', '17']
        for j, l in enumerate(head):
            lbl = Gtk.Label(label=l)
            lbl.override_font(font)
            lbl.set_hexpand(True)
            lbl.set_halign(Gtk.Align.CENTER)
            grid.attach(lbl, j + 2, 0, 1, 1)
        cat = ['lum', 'normal', 'short', 'far']
        for i, c in enumerate(cat):
            for j, o in enumerate(getattr(boss.opts, c)):
                lbl = Gtk.Label(label=str(o))
                lbl.set_hexpand(True)
                lbl.set_halign(Gtk.Align.CENTER)
                grid.attach(lbl, j + 2, i + 1, 1, 1)

        frame = Gtk.Frame()
        frame.add(grid)
        frame.set_halign(Gtk.Align.CENTER)
        frame.set_valign(Gtk.Align.CENTER)
        self.pack_start(frame, True, False, 0)


class LangPage(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        boss = _boss()
        self.langs = ['es', 'en', 'de', 'ca']
        init_lang = self.langs.index(boss.opts.lang)
        self.set_border_width(6)

        buttbox = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL)
        buttbox.set_layout(Gtk.ButtonBoxStyle.SPREAD)
        label = Gtk.Label(label=_("Cambiar lenguage"))
        buttbox.pack_start(label, True, True, 0)

        store = Gtk.ListStore(str)
        store.append([_('espanol')])
        store.append([_('ingles')])
        store.append([_('aleman')])
        store.append([_('catalan')])
        combo = Gtk.ComboBox.new_with_model(store)
        cell = Gtk.CellRendererText()
        combo.pack_start(cell, True)
        combo.add_attribute(cell, 'text', 0)
        combo.set_size_request(100, 28)
        combo.connect('changed', self.lang_set_cb)
        combo.set_active(init_lang)
        buttbox.pack_start(combo, True, True, 0)
        self.pack_start(buttbox, False, False, 0)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        align = Gtk.Alignment(xalign=0.5, yalign=0.5)
        label = Gtk.Label(label=_("Los cambios tendran lugar depues de reiniciar la aplicacion"))
        label.set_size_request(300, -1)
        label.set_justify(Gtk.Justification.CENTER)
        label.set_line_wrap(True)
        align.add(label)
        hbox.pack_start(align, True, True, 0)
        hbox.set_border_width(6)
        self.pack_start(hbox, False, False, 0)

    def lang_set_cb(self, combo):
        _boss().opts.lang = self.langs[combo.get_active()]


class PngPage(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self.set_border_width(6)
        boss = _boss()

        for opt_lbl, opt_attr in [(_("Horizontal"), 'hsize'), (_("Vertical"), 'vsize')]:
            buttbox = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL)
            buttbox.set_layout(Gtk.ButtonBoxStyle.EDGE)
            label = Gtk.Label(label=opt_lbl)
            buttbox.pack_start(label, True, True, 0)
            entry = Gtk.Entry()
            entry.set_text(str(getattr(boss.opts, opt_attr)))
            entry.connect('changed', self.png_set_cb, opt_attr)
            buttbox.pack_start(entry, True, True, 0)
            self.pack_start(buttbox, False, False, 0)

        buttbox = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL)
        buttbox.set_layout(Gtk.ButtonBoxStyle.EDGE)
        lcheck = Gtk.CheckButton(label=_("Etiquetas"))
        buttbox.pack_start(lcheck, True, True, 0)
        active = boss.opts.labels == 'true'
        lcheck.set_active(active)
        lcheck.connect('toggled', self.png_lbl_cb)
        self.pack_start(buttbox, False, False, 0)

    def png_set_cb(self, entry, lbl):
        boss = _boss()
        opt = getattr(boss.opts, lbl)
        try:
            opt = int(entry.get_text())
            setattr(boss.opts, lbl, opt)
        except ValueError:
            entry.set_text(str(opt))

    def png_lbl_cb(self, but):
        _boss().opts.labels = ['false', 'true'][int(but.get_active())]
