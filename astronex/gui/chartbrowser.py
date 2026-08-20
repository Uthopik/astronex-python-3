# -*- coding: utf-8 -*-
from copy import copy

import cairo
from gi.repository import Gtk, Gdk, Pango, PangoCairo

from astronex.drawing.coredraw import CoreMixin
from astronex.drawing.dispatcher import DrawMixin, AspectManager
from astronex.drawing.roundedcharts import RadixChart
from astronex.gui.mainnb import Slot
from astronex.gui.mixer import MixerPanel
from astronex.gui.import_dlg import ImportPanel
from astronex.gui.couples import CouplesPanel
from astronex.gui.searchview import SearchView
from astronex.utils import parsestrtime
from astronex.extensions.path import path


def _boss():
    from astronex.boss import boss
    return boss


def _curr():
    return _boss().get_state()


_chart_singleton = None


def _chart():
    global _chart_singleton
    if _chart_singleton is None:
        _chart_singleton = _curr().newchart()
    return _chart_singleton


def _combo_text(combo):
    it = combo.get_active_iter()
    if it is not None:
        return combo.get_model()[it][0]
    child = combo.get_child()
    if child is not None:
        return child.get_text()
    return ""


class ChartBrowserWindow(Gtk.Window):
    def __init__(self, parent):
        boss = _boss()
        curr = _curr()
        global _chart_singleton
        _chart_singleton = curr.newchart()
        self.parent_win = parent
        Gtk.Window.__init__(self)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_transient_for(parent)
        self.set_title(_("Explorador"))
        # ESC o la X = OCULTAR la ventana (no destruirla) y reutilizarla luego.
        # Destruir esta ventana en GTK3/WSLg provocaba un segfault que mataba
        # toda la app; al no destruirla NUNCA durante la sesion se evita el
        # camino de finalizacion que crasheaba. La ventana se retiene en
        # winnex.browser y se vuelve a mostrar con Ctrl-B. Se quito el
        # accel-group ESC->destroy, el connect('destroy') y el
        # set_destroy_with_parent (todos parte del camino de destruccion).
        self.connect('key-press-event', self.on_key_press)
        self.connect('delete-event', self.on_delete)
        self.connect('focus-out-event', self.on_state)
        self.connect('configure-event', self.on_configure_event)

        notebook = Gtk.Notebook()
        notebook.set_tab_pos(Gtk.PositionType.LEFT)
        notebook.connect('switch-page', self.page_select)

        def add_tab(panel, text):
            label = Gtk.Label(label=text)
            label.set_angle(90)
            notebook.append_page(panel, label)

        add_tab(BrowserPanel(parent), _("Explorador"))
        add_tab(MixerPanel(parent), _("Mezclador"))
        add_tab(ImportPanel(parent), _("Importacion AAF"))
        add_tab(CouplesPanel(parent), _("Parejas"))

        self.notebook = notebook
        self.add(notebook)
        self.set_default_size(650, 400)
        self.show_all()
        wpos = self.get_position()
        self.pos_x = wpos[0]
        self.pos_y = wpos[1]

    def on_configure_event(self, widget, event):
        self.pos_x = event.x
        self.pos_y = event.y

    def page_select(self, nb, page, pnum):
        page = nb.get_nth_page(pnum)
        try:
            if pnum == 0 and nb.get_nth_page(1).changes:
                page.relist()
        except AttributeError:
            pass
        if page.__class__ == CouplesPanel:
            page.save_couples()
        title = nb.get_tab_label(page).get_text()
        self.set_title(title)

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self._save_on_close()
            self.hide()
            return True
        return False

    def on_state(self, e, event):
        boss = _boss()
        if self.notebook.get_nth_page(1).changes:
            boss.mpanel.browser.tables.emit('changed')
            boss.mpanel.browser.relist('')

    def on_delete(self, widget, event):
        # No destruir: ocultar (return True evita el destroy por defecto) y
        # ejecutar la misma limpieza/guardado que antes hacia cb_exit. NO se
        # pone parent.browser = None: la ventana se conserva y se reutiliza.
        self._save_on_close()
        self.hide()
        return True

    def _save_on_close(self):
        boss = _boss()
        if self.notebook.get_nth_page(1).changes:
            boss.mpanel.browser.tables.emit('changed')
            boss.mpanel.browser.relist('')
        self.notebook.get_nth_page(3).save_couples()


class BrowserPanel(Gtk.Box):
    def __init__(self, parent):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.HORIZONTAL)
        boss = _boss()
        curr = _curr()

        self.chartview = None
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # tables
        liststore = Gtk.ListStore(str)
        self.tables = Gtk.ComboBox.new_with_model_and_entry(liststore)
        self.tables.set_entry_text_column(0)
        self.tables.set_size_request(228, -1)
        self.tables.get_child().set_editable(False)
        self.tables.connect('changed', self.on_tables_changed)
        tablelist = curr.datab.get_databases()

        for c in tablelist:
            liststore.append([c])
        index = 0
        for i, r in enumerate(liststore):
            if r[0] == curr.database:
                index = i
                break
        self.tables.set_active(index)

        but = Gtk.Button()
        img = Gtk.Image()
        appath = boss.app.appath
        imgfile = path.joinpath(appath, "astronex/resources/refresh-18.png")
        img.set_from_file(str(imgfile))
        but.set_image(img)
        but.connect('clicked', self.on_refresh_clicked, self.tables)
        hhbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hhbox.pack_start(self.tables, False, False, 0)
        hhbox.pack_start(but, False, False, 0)
        vbox.pack_start(hhbox, False, False, 0)

        # chart list
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
        sel = self.chartview.get_selection()
        sel.set_mode(Gtk.SelectionMode.SINGLE)
        sel.connect('changed', self.on_sel_changed)
        sel.select_path(Gtk.TreePath.new_from_indices([0]))
        self.chartview.grab_focus()

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.add(self.chartview)
        vbox.pack_start(sw, True, True, 0)

        hbox.pack_start(vbox, False, False, 0)
        hbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)
        self.chsnap = ChartSnapshot(parent.boss)
        self.chsnap.set_size_request(400, 400)
        hbox.pack_start(self.chsnap, True, True, 0)
        frame = Gtk.Frame()
        frame.set_border_width(6)
        frame.add(hbox)
        self.add(frame)

    def on_refresh_clicked(self, but, combo):
        combo.emit('changed')

    def findchart(self, first, last):
        model = self.chartview.get_model()
        it = model.get_iter_first()
        while it:
            tfirst, _, tlast = model.get_value(it, 0).partition(',')
            if first == tfirst and last == tlast:
                self.chartview.get_selection().select_path(model.get_path(it))
                break
            it = model.iter_next(it)

    def on_tables_changed(self, combo):
        if combo.get_active() == -1:
            return
        curr = _curr()
        if self.chartview is not None:
            chartmodel = Gtk.ListStore(str, int)
            chartlist = curr.datab.get_chartlist(_combo_text(self.tables))
            for c in chartlist:
                glue = ", "
                if c[2] == '':
                    glue = ''
                chartmodel.append([c[2] + glue + c[1], int(c[0])])
            self.chartview.set_model(chartmodel)
            self.chartview.get_selection().select_path(Gtk.TreePath.new_from_indices([0]))

    def on_sel_changed(self, sel):
        curr = _curr()
        model, it = sel.get_selected()
        if not it:
            sel.select_path(Gtk.TreePath.new_from_indices([0]))
            model, it = sel.get_selected()
        if not it:
            return
        id = model.get_value(it, 1)
        table = _combo_text(self.tables)
        curr.datab.load_chart(table, id, _chart())
        try:
            self.chsnap.redraw()
        except AttributeError:
            pass

    def on_chart_activated(self, view, path_, col):
        curr = _curr()
        model, it = view.get_selection().get_selected()
        id = model.get_value(it, 1)
        chart = curr.charts[Slot.storage]
        table = _combo_text(self.tables)
        curr.datab.load_chart(table, id, chart)
        curr.add_to_pool(copy(chart), Slot.overwrite)
        from astronex.gui.mainnb import MainPanel
        MainPanel.actualize_pool(Slot.storage, chart)

    def relist(self):
        curr = _curr()
        liststore = Gtk.ListStore(str)
        tablelist = curr.datab.get_databases()
        for c in tablelist:
            liststore.append([c])
        self.tables.set_model(liststore)


class ChartSnapshot(Gtk.DrawingArea):
    def __init__(self, boss):
        self.boss = boss
        self.opts = boss.opts
        Gtk.DrawingArea.__init__(self)
        self.connect("draw", self.dispatch)
        self.drawer = SnapMixin(boss.opts, self)

    def dispatch(self, da, cr):
        alloc = self.get_allocation()
        w = alloc.width
        h = alloc.height
        cr.rectangle(0, 0, w, h)
        cr.clip()
        cr.set_source_rgb(1.0, 1.0, 0.95)
        cr.rectangle(0, 0, w, h)
        cr.fill()
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.set_line_width(float(self.opts.base))

        ch = _chart()
        if not ch.houses:
            return True
        chartobject = RadixChart(ch, None)
        # Aislar el translate() interno de la carta con save/restore en vez de
        # que d_label use cr.identity_matrix(): en GTK3 identity_matrix descarta
        # la transformacion base del widget (posicion/escala que aplica GTK al
        # DrawingArea), descolocando la etiqueta. Asi d_label dibuja en las
        # coordenadas locales correctas del preview.
        cr.save()
        self.drawer.draw_nat(cr, w, h, chartobject)
        cr.restore()
        self.d_label(cr, w, h, ch)
        return True

    def redraw(self):
        self.queue_draw()

    def d_label(self, cr, w, h, chart):
        layout = PangoCairo.create_layout(cr)
        font = Pango.FontDescription.from_string(self.opts.font)
        font.set_size(7 * Pango.SCALE)
        layout.set_font_description(font)
        date, time = parsestrtime(chart.date)
        date = date + " - " + time.split(" ")[0]
        name = chart.first + " " + chart.last
        layout.set_text('%s  (%s)' % (name, date), -1)
        # Limitar el texto al ancho del preview y alinearlo a la derecha. Si no
        # cabe (nombre largo o escalado de fuente/HiDPI), se recorta el INICIO
        # (el nombre) con puntos suspensivos para que la FECHA quede SIEMPRE
        # visible, en vez de que el texto se salga cortado por la izquierda.
        layout.set_width(int(max(10, w - 10) * Pango.SCALE))
        layout.set_alignment(Pango.Alignment.RIGHT)
        layout.set_ellipsize(Pango.EllipsizeMode.START)
        cr.set_source_rgb(0.0, 0, 0.5)
        cr.move_to(5, h - 12)
        PangoCairo.show_layout(cr, layout)


R_ASP = 0.435


class SnapMixin(CoreMixin):
    def __init__(self, opts, surface):
        self.opts = opts
        self.surface = surface
        self.aspmanager = AspectManager(_boss(), self.get_gw, self.get_uni, self.get_nw,
                                        DrawMixin.planetmanager, opts.zodiac.aspcolors, opts.base)
        CoreMixin.__init__(self, opts.zodiac, surface)

    def draw_nat(self, cr, width, height, chartob):
        cx, cy = width / 2, height / 2
        radius = min(cx, cy)
        cr.translate(cx, cy)

        self.d_radial_lines(cr, radius, chartob)
        self.make_all_rulers(cr, radius, chartob)
        self.draw_signs(cr, radius, chartob)
        self.draw_planets(cr, radius, chartob)
        self.make_plines(cr, radius, chartob, 'EXT')
        self.draw_cusps(cr, radius, chartob)
        self.d_year_lines(cr, radius, chartob)
        self.d_golden_points(cr, radius, chartob)
        self.d_cross_points(cr, radius, chartob)
        self.aspmanager.manage_aspects(cr, radius * R_ASP, chartob.get_planets())
        self.make_plines(cr, radius, chartob, 'INN')
        self.d_inner_circles(cr, radius)

    def get_gw(self):
        return False

    def get_uni(self):
        return True

    def get_nw(self, f=None):
        return []
