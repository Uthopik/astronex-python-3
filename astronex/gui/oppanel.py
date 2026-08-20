# -*- coding: utf-8 -*-
from gi.repository import Gtk

from astronex.extensions.path import path


def _boss():
    from astronex.boss import boss
    return boss


def _curr():
    return _boss().get_state()


class OpPanel(Gtk.Box):
    images = {
        'charts': "chart.png",
        'data': "data.png",
        'bio': "biog.png",
        'diagram': "diag.png",
        'clicks': "click.png",
        'transit': "transit.png",
        'double1': 'double1.png',
        'double2': 'double2.png',
        'triple1': 'triple1.png',
        'triple2': 'triple2.png',
    }

    tooltips = {
        'charts': _("Cartas"),
        'data': _("Datos / Hojas"),
        'bio': _("Biografias"),
        'diagram': _("Diagramas"),
        'clicks': _("Clics"),
        'transit': _("Transitos"),
        'double1': _("Comparacion doble (maestro)"),
        'double2': _("Comparacion doble con clic"),
        'triple1': _("Comparacion triple (maestro)"),
        'triple2': _("Comparacion triple con clic"),
    }

    opdoubles = [(_('CRadix'), 'draw_nat'),
                 (_('CCasas'), 'draw_house'),
                 (_('Nodal de Casas'), 'draw_nod'),
                 (_('Alma'), 'draw_soul'),
                 (_('Dharma'), 'draw_dharma'),
                 (_('Nodal'), 'draw_ur_nodal'),
                 (_('Local'), 'draw_local'),
                 (_('Perfil'), 'draw_prof'),
                 (_('Integracion'), 'draw_int'),
                 (_('Clics Ind.'), 'draw_single'),
                 (_('Radix Alma'), 'draw_radsoul')]

    optriples = [(_('Casas-Casas'), 'click_hh'),
                 (_('Nodal-Nodal'), 'click_nn'),
                 (_('Casas-Nodal'), 'click_hn'),
                 (_('Nodal-Casas'), 'click_nh'),
                 (_('Alma-Alma'), 'click_ss'),
                 (_('Radix-Radix'), 'click_rr'),
                 (_('Clic Subjetivo'), 'subject_click')]

    buttons = {
        'charts': [
            (_('CRadix'), 'draw_nat'),
            (_('CCasas'), 'draw_house'),
            (_('Nodal de Casas'), 'draw_nod'),
            (_('Alma'), 'draw_soul'),
            (_('Dharma'), 'draw_dharma'),
            (_('Nodal'), 'draw_ur_nodal'),
            (_('Local'), 'draw_local'),
            (_('Perfil'), 'draw_prof'),
            (_('Integracion'), 'draw_int'),
            (_('Clic Individual'), 'draw_single'),
            (_('Clic Radix-Alma'), 'draw_radsoul'),
            (_('Radix-Dharma'), 'draw_raddharma'),
        ],
        'data': [
            (_('CRadix'), 'dat_nat'),
            (_('CCasas'), 'dat_house'),
            (_('Nodales'), 'dat_nod'),
            (_('Progresion de la edad Radix'), 'prog_nat'),
            (_('Progresion de la edad Carta Nodal'), 'prog_nod'),
            (_('Progresion de la edad Carta Local'), 'prog_local'),
            (_('Progresion de la edad Carta del Alma'), 'prog_soul'),
        ],
        'bio': [
            (_('Biografia Radix'), 'bio_nat'),
            (_('Biografia Nodal'), 'bio_nod'),
            (_('Biografia Alma'), 'bio_soul'),
            (_('Biografia Dharma'), 'bio_dharma'),
        ],
        'diagram': [
            (_('Comparacion pareja I'), 'compo_one'),
            (_('Comparacion pareja II'), 'compo_two'),
            (_('Estrella de ascenso'), 'ascent_star'),
            (_('Estrella maravillosa'), 'wundersensi_star'),
            (_('Analisis de polaridades'), 'polar_star'),
            (_('Uniones corona'), 'crown_comp'),
            (_('Panal de la pareja'), 'paarwabe_plot'),
            (_('Comparacion PE'), 'comp_pe'),
            (_('Contra horoscopos'), 'click_counterpanel'),
            (_('Cuadrantes dinamicos'), 'dyn_cuad'),
            (_('Clic Cuadrantes dinamicos'), 'dyn_cuad2'),
            (_('Estrellas dinamicas'), 'dyn_stars'),
        ],
        'clicks': [
            (_('Casas-Casas'), 'click_hh'),
            (_('Nodal-Nodal'), 'click_nn'),
            (_('Casas-Nodal'), 'click_hn'),
            (_('Nodal-Casas'), 'click_nh'),
            (_('Alma-Alma'), 'click_ss'),
            (_('Radix-Radix'), 'click_rr'),
            (_('Radix-Alma'), 'click_rs'),
            (_('Alma-Nodal'), 'click_sn'),
            (_('Clic Subjetivo'), 'subject_click'),
            (_('Puente'), 'click_bridge'),
        ],
        'transit': [
            (_('Transitos'), 'draw_transits'),
            (_('Radix con transitos'), 'rad_and_transit'),
            (_('Progresion secundaria'), 'sec_prog'),
            (_('Revolucion solar'), 'solar_rev'),
        ],
    }

    singles = ['charts', 'data', 'bio', 'diagram', 'clicks', 'transit']
    doublebuts = ['double1', 'double2']
    triplebuts = ['triple1', 'triple2']

    def __init__(self, manager):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self.boss = manager

        self.groups_table = Gtk.Table(n_rows=2, n_columns=5, homogeneous=True)
        self.pack_start(self.groups_table, False, False, 0)
        self.current_button = None
        self.init_button = None

        self.notebook = Gtk.Notebook()
        self.notebook.set_show_tabs(False)
        self.notebook.set_show_border(False)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.add(self.notebook)
        self.pack_start(sw, True, True, 0)

        self.nb_sections = 0
        self.sections_button_group = None

        self.namebuttons = ['charts', 'data', 'clicks', 'diagram', 'bio', 'transit']
        for group in self.namebuttons:
            self.append_single_group(group, self.buttons[group])
        self.prev_mode = 'simple'
        page = self.nb_sections
        for i, group in enumerate(['double1', 'double2']):
            self.append_mult_group(group, i, page)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.make_lists(hbox, 2, self.on_seldouble_changed)
        self.notebook.append_page(hbox)
        self.nb_sections += 1
        page = self.nb_sections
        for i, group in enumerate(['triple1', 'triple2']):
            self.append_mult_group(group, i, page, offset=4)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.make_lists(hbox, 3, self.on_seltriple_changed)
        self.notebook.append_page(hbox)

    def append_mult_group(self, name, pos, page, offset=3):
        boss = self.boss
        appath = boss.app.appath
        button = Gtk.RadioButton.new_from_widget(self.sections_button_group)
        img = Gtk.Image()
        imgfile = path.joinpath(appath, "astronex/resources/" + self.images[name])
        img.set_from_file(str(imgfile))
        button.set_image(img)
        button.set_mode(False)
        button.page = page
        button.name = name
        button.set_tooltip_text(self.tooltips.get(name, name))
        button.connect('toggled', self.on_catalog_button_toggled)
        r = pos % 2
        c = (pos // 2) + offset
        self.groups_table.attach(button, c, c + 1, r, r + 1)

    def make_lists(self, hbox, n, callback):
        for i in range(n):
            model = Gtk.ListStore(str, str)
            view = Gtk.TreeView(model=model)
            for o in self.opdoubles:
                model.append(o)
            cell = Gtk.CellRendererText()
            cell.weight = 600
            column = Gtk.TreeViewColumn(None, cell, text=0)
            view.append_column(column)
            view.set_headers_visible(False)
            view.set_enable_search(False)
            sel = view.get_selection()
            sel.set_mode(Gtk.SelectionMode.SINGLE)
            sel.connect('changed', callback, i)
            hbox.pack_start(view, True, True, 0)
            if i < n - 1:
                hbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)

    def append_single_group(self, name, group):
        page = self.nb_sections
        self.nb_sections += 1
        boss = self.boss
        appath = boss.app.appath

        if not self.sections_button_group:
            button = Gtk.RadioButton.new(None)
            self.current_button = button
            self.init_button = button
        else:
            button = Gtk.RadioButton.new_from_widget(self.sections_button_group)
        img = Gtk.Image()
        imgfile = path.joinpath(appath, "astronex/resources/" + self.images[name])
        img.set_from_file(str(imgfile))
        button.set_image(img)
        self.sections_button_group = button
        button.set_mode(False)
        button.page = page
        button.name_id = name
        button.set_tooltip_text(self.tooltips.get(name, name))
        button.connect('toggled', self.on_catalog_button_toggled)

        pos = self.namebuttons.index(name)
        r = pos % 2
        c = pos // 2
        self.groups_table.attach(button, c, c + 1, r, r + 1)
        self.notebook.append_page(self.widget_table_create(group))

    def widget_table_create(self, ops):
        model = Gtk.ListStore(str, str)
        view = Gtk.TreeView(model=model)
        for o in ops:
            model.append(o)
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

    def delta_select(self, delta):
        ix = self.notebook.get_current_page()
        page = self.notebook.get_nth_page(ix)
        sel = page.get_selection()
        model, it = sel.get_selected()
        n = model.iter_n_children(None)
        try:
            new_idx = (model.get_path(it)[0] + delta) % n
            sel.select_path(Gtk.TreePath.new_from_indices([new_idx]))
        except (TypeError, AttributeError):
            sel.select_path(Gtk.TreePath.new_from_indices([0]))

    def swap_ops(self, side=None):
        ix = self.notebook.get_current_page()
        page = self.notebook.get_nth_page(ix).get_children()
        if not side:
            i1 = 0
            i2 = 2
        else:
            sides = ['left', None, 'up', None, 'right']
            i1 = sides.index(side)
            i2 = (i1 + 2) % 6
        sel1 = page[i1].get_selection()
        model1, iter1 = sel1.get_selected()
        sel2 = page[i2].get_selection()
        model2, iter2 = sel2.get_selected()
        sel1.select_path(model2.get_path(iter2))
        sel2.select_path(model1.get_path(iter1))

    def delta_double_select(self, delta, side, ontriple=False):
        curr = _curr()
        sides = ['left', None, 'right']
        if ontriple:
            sides = ['left', None, 'up', None, 'right']
        ix = self.notebook.get_current_page()
        page = self.notebook.get_nth_page(ix).get_children()
        ixsel = otherix = 0
        for i, s in enumerate(sides):
            if not s or s == 'up':
                continue
            if s == side:
                ixsel = i
            else:
                otherix = i
        sel = page[ixsel].get_selection()
        model, it = sel.get_selected()
        n = model.iter_n_children(None)
        try:
            new_idx = (model.get_path(it)[0] + delta) % n
            sel.select_path(Gtk.TreePath.new_from_indices([new_idx]))
        except (TypeError, AttributeError):
            sel.select_path(Gtk.TreePath.new_from_indices([0]))
        if curr.clickmode == 'click':
            model, it = sel.get_selected()
            sel = page[otherix].get_selection()
            sel.select_path(Gtk.TreePath.new_from_indices([model.get_path(it)[0]]))

    def delta_triple_select(self, delta, side):
        if side == 'up':
            ix = self.notebook.get_current_page()
            page = self.notebook.get_nth_page(ix).get_children()
            sel = page[2].get_selection()
            model, it = sel.get_selected()
            n = model.iter_n_children(None)
            try:
                new_idx = (model.get_path(it)[0] + delta) % n
                sel.select_path(Gtk.TreePath.new_from_indices([new_idx]))
            except (TypeError, AttributeError):
                sel.select_path(Gtk.TreePath.new_from_indices([0]))
        else:
            self.delta_double_select(delta, side, True)

    def on_catalog_button_toggled(self, button):
        boss = _boss()
        curr = _curr()
        pmode = ['', 'master', 'click']
        page = button.page
        name = getattr(button, 'name_id', None) or getattr(button, 'name', None)
        self.current_button = button
        if name in self.singles:
            curr.opmode = 'simple'
            curr.clickmode = 'master'
            if name == 'clicks':
                curr.clickmode = 'click'
        else:
            curr.opmode = name[:-1]
            curr.clickmode = pmode[int(name[-1])]

        self.notebook.set_current_page(page)
        TP = lambda n: Gtk.TreePath.new_from_indices([n])
        try:
            sel = self.notebook.get_nth_page(page).get_selection()
            m, i = sel.get_selected()
            if i is None:
                sel.select_path(TP(0))
            sel.emit('changed')
            curr.set_list(name)
        except AttributeError:
            if curr.opmode == 'double':
                left, _, right = self.notebook.get_nth_page(page).get_children()
                left.get_selection().select_path(TP(0))
                left.get_selection().emit('changed')
                if curr.clickmode == 'click':
                    right.get_selection().select_path(TP(0))
                else:
                    m, i = right.get_selection().get_selected()
                    if i is None or m.get_path(i)[0] != 2:
                        right.get_selection().select_path(TP(1))
                right.get_selection().emit('changed')
                curr.set_list(name)
            elif curr.opmode == 'triple':
                left, _, up, _, right = self.notebook.get_nth_page(page).get_children()
                if curr.clickmode == 'click':
                    left.get_selection().select_path(TP(0))
                    right.get_selection().select_path(TP(0))
                else:
                    left.get_selection().select_path(TP(2))
                    right.get_selection().select_path(TP(1))
                left.get_selection().emit('changed')
                right.get_selection().emit('changed')
                self.subst_tripleup(up)
                up.get_selection().select_path(TP(0))
                up.get_selection().emit('changed')
        return False

    def on_sel_changed(self, sel):
        boss = _boss()
        curr = _curr()
        model, it = sel.get_selected()
        if not it:
            return
        op = model.get_value(it, 1)
        curr.set_op(op)
        if op in ['compo_one', 'compo_two', 'click_counterpanel', 'ascent_star', 'wundersensi_star',
                  'polar_star', 'crown_comp', 'paarwabe_plot', 'dyn_cuad2']:
            curr.clickmode = 'click'
        elif op in ['dyn_cuad', 'dyn_stars']:
            curr.clickmode = 'master'
        if op in ['draw_transits', 'draw_prof', 'subject_click']:
            boss.da.toggle_menulist('ea', 'add')
        else:
            boss.da.toggle_menulist('ea', 'remove')
        if op in ['draw_nat', 'draw_nod', 'bio_nat', 'bio_nod']:
            boss.da.toggle_menulist('pez', 'add')
            boss.da.redraw_auxwins(True)
        else:
            boss.da.toggle_menulist('pez', 'remove')
        if op == 'draw_nat':
            boss.da.toggle_menulist('hz', 'add')
        else:
            boss.da.toggle_menulist('hz', 'remove')
        if op in ['click_hh', 'click_nn', 'click_hn', 'click_nh', 'click_ss', 'click_rr', 'click_rs', 'click_sn']:
            boss.da.toggle_menulist('ego', 'add')
            boss.da.toggle_menulist('acl', 'add')
        else:
            boss.da.toggle_menulist('acl', 'remove')
            boss.da.toggle_menulist('ego', 'remove')
        boss.da.redraw()

    def subst_tripleup(self, up):
        curr = _curr()
        lists = {'master': self.opdoubles, 'click': self.optriples}
        model = Gtk.ListStore(str, str)
        for o in lists[curr.clickmode]:
            model.append(o)
        up.set_model(model)

    def on_seldouble_changed(self, sel, ix):
        boss = _boss()
        curr = _curr()
        model, it = sel.get_selected()
        if not it:
            return
        op = model.get_value(it, 1)
        side = ('opleft', 'opright')[ix]
        setattr(curr, side, op)
        boss.da.redraw()

    def on_seltriple_changed(self, sel, ix):
        boss = _boss()
        curr = _curr()
        model, it = sel.get_selected()
        if not it:
            return
        op = model.get_value(it, 1)
        side = ('opleft', 'opup', 'opright')[ix]
        setattr(curr, side, op)
        boss.da.redraw()
