# -*- coding: utf-8 -*-
import os
import sys
import shlex
import subprocess

import cairo
from gi.repository import Gtk, Pango, PangoCairo
import PIL.Image

from astronex.drawing.dispatcher import DrawMixin
from astronex.utils import parsestrtime


def _boss():
    from astronex.boss import boss
    return boss


def _curr():
    return _boss().get_state()


_opts = None
_minim = None
MAGICK_SCALE = 0.002

# Instancia unica reutilizada del dialogo de exportacion. En GTK3/WSLg destruir
# el dialogo (dialog.destroy()) tras run() provoca un segfault que mata toda la
# app. Igual que HelpWindow, retenemos una sola instancia y la OCULTAMOS en vez
# de destruirla; nunca se finaliza durante la sesion -> no hay segfault.
_export_dialog = None


def ajusta_extension(filename, dialog):
    '''Garantiza que el nombre acabe en .png/.jpg/.jpeg. Si el usuario escribe
    el nombre a mano sin extension, PIL no sabe en que formato guardar y lanza
    "unknown file extension"; ademas la rama que convierte RGBA->RGB para JPEG
    se decide por la extension. Se usa el tipo elegido en el desplegable.'''
    root, ext = os.path.splitext(filename)
    if ext.lower() in ('.png', '.jpg', '.jpeg'):
        return filename
    tipo = 'png'
    try:
        tipo = (dialog.typefile_chooser.get_active_text() or 'png').lower()
    except Exception:
        pass
    if tipo not in ('png', 'jpg', 'jpeg'):
        tipo = 'png'
    return root + '.' + tipo


def guardar_imagen(im, filename):
    '''Guarda la imagen (PIL, modo RGBA) en filename.

    JPEG no admite canal alfa: PIL lanza "cannot write mode RGBA as JPEG" (el
    error que reporto Elias). Para .jpg/.jpeg se compone antes sobre fondo
    blanco usando el alfa como mascara. Vive aqui para que el guardado de la
    ventana principal y el del Planetograma usen exactamente el mismo codigo.'''
    ext = os.path.splitext(filename)[1].lower()
    if ext in ('.jpg', '.jpeg'):
        fondo = PIL.Image.new('RGB', im.size, (255, 255, 255))
        fondo.paste(im, mask=im.split()[3])  # canal alfa como mascara
        fondo.info['dpi'] = im.info['dpi']
        fondo.save(filename, dpi=fondo.info['dpi'])
    else:
        im.save(filename, dpi=im.info['dpi'])


def get_export_dialog(pg=False):
    '''Devuelve la instancia unica del dialogo, creada una sola vez y reutilizada
    oculta. Refresca el estado por-uso (nombre por defecto / carpeta) en cada
    apertura para conservar el comportamiento del dialogo recien construido.'''
    global _export_dialog
    if _export_dialog is None:
        _export_dialog = ImageExportDialog()
    _export_dialog.prepare(pg)
    _export_dialog.show_all()
    return _export_dialog


class ImageExportDialog(Gtk.Dialog):
    '''Save image config dialog'''

    def __init__(self, pg=False):
        Gtk.Dialog.__init__(self,
                            title=_("Exportar como imagen"),
                            parent=None,
                            destroy_with_parent=False)
        self.add_buttons(_("_Cancelar"), Gtk.ResponseType.CANCEL,
                         _("_Guardar"), Gtk.ResponseType.OK)
        # NO se conecta 'delete-event': se conduce con run(), que ya intercepta
        # ESC y la X (devuelve DELETE_EVENT y el bucle retorna sin destruir).
        # Como ya no llamamos a destroy() (solo hide()), no hay segfault. Un
        # 'delete-event' propio que devuelva True es innecesario y arriesga
        # interferir con el bucle de run().

        content = self.get_content_area()
        content.set_border_width(3)
        content.set_spacing(6)

        content.pack_start(self.make_control(), False, False, 0)
        content.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), True, True, 0)
        chooser = Gtk.FileChooserWidget(action=Gtk.FileChooserAction.SAVE)
        content.pack_start(chooser, False, False, 0)
        self.chooser = chooser
        self.chooser.set_size_request(600, 400)

        self.set_default_response(Gtk.ResponseType.OK)
        filt = Gtk.FileFilter()
        filt.add_mime_type("image/png")
        filt.add_mime_type("image/jpeg")
        filt.set_name(_("Imagen"))
        self.chooser.add_filter(filt)
        self.chooser.set_do_overwrite_confirmation(True)

        self.prepare(pg)

    def prepare(self, pg=False):
        '''Refresca el estado por-uso (nombre/carpeta por defecto) en cada
        apertura, segun la carta y el modo (pg = planetograma).'''
        curr = _curr()
        boss = _boss()
        if pg:
            name = curr.curr_chart.first + "_" + curr.curr_chart.last + "_pg"
        else:
            suffix = boss.suffixes.get(curr.curr_op, "rx")
            name = curr.curr_chart.first + "_" + suffix

        ext = self.typefile_chooser.get_active_text()
        self.chooser.set_current_name(name + "." + ext)
        self.chooser.set_current_folder(os.path.expanduser("~"))

    def make_control(self):
        boss = _boss()
        tab = Gtk.Table(n_rows=2, n_columns=3)
        tab.set_row_spacings(6)
        tab.set_col_spacings(12)
        tab.set_homogeneous(False)
        tab.set_border_width(6)

        def make_spin_box(label_text, value, attr):
            buttbox = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL)
            buttbox.set_layout(Gtk.ButtonBoxStyle.EDGE)
            label = Gtk.Label(label=label_text)
            buttbox.pack_start(label, True, True, 0)
            adj = Gtk.Adjustment(value=int(value), lower=1, upper=10000,
                                 step_increment=1, page_increment=1, page_size=0)
            spin = Gtk.SpinButton()
            spin.set_adjustment(adj)
            spin.set_alignment(1.0)
            spin.set_numeric(True)
            adj.connect('value-changed', self.spin_imgsize, spin, attr)
            spin.connect('changed', self.entry_imgsize, attr)
            buttbox.pack_start(spin, True, True, 0)
            return buttbox

        tab.attach(make_spin_box(_("Anchura"), boss.opts.hsize, 'hsize'), 0, 1, 0, 1)
        tab.attach(make_spin_box(_("Altura"), boss.opts.vsize, 'vsize'), 0, 1, 1, 2)

        buttbox = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL)
        buttbox.set_layout(Gtk.ButtonBoxStyle.EDGE)
        label = Gtk.Label(label=_("Resolucion"))
        buttbox.pack_start(label, True, True, 0)
        adj = Gtk.Adjustment(value=int(boss.opts.resolution), lower=1, upper=600,
                             step_increment=1, page_increment=1, page_size=0)
        res = Gtk.SpinButton()
        res.set_adjustment(adj)
        res.set_alignment(1.0)
        res.set_numeric(True)
        adj.connect('value-changed', self.spin_change_res, res)
        res.connect('changed', self.entry_change_res)
        buttbox.pack_start(res, True, True, 0)
        tab.attach(buttbox, 1, 2, 0, 1)

        buttbox = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL)
        buttbox.set_layout(Gtk.ButtonBoxStyle.EDGE)
        label = Gtk.Label(label=_("Tipo"))
        buttbox.pack_start(label, True, True, 0)
        combo = Gtk.ComboBoxText()
        combo.append_text(_('png'))
        combo.append_text(_('jpg'))
        combo.set_active(0)
        combo.connect("changed", self.typefile_changed)
        self.typefile_chooser = combo
        buttbox.pack_start(combo, True, True, 0)
        tab.attach(buttbox, 1, 2, 1, 2)
        return tab

    def typefile_changed(self, combo):
        ext = combo.get_active_text()
        base = os.path.basename(self.chooser.get_filename() or '')
        root, _oldext = os.path.splitext(base)
        self.chooser.set_current_name(root + "." + ext)

    def spin_imgsize(self, adj, spin, lbl):
        opt = spin.get_value_as_int()
        setattr(_boss().opts, lbl, opt)

    def entry_imgsize(self, spin, lbl):
        try:
            opt = int(spin.get_text())
        except ValueError:
            return
        setattr(_boss().opts, lbl, opt)

    def spin_change_res(self, adj, spin):
        opt = spin.get_value_as_int()
        _boss().opts.resolution = opt

    def entry_change_res(self, spin):
        try:
            opt = int(spin.get_text())
        except ValueError:
            return
        _boss().opts.resolution = opt


class DrawPng(object):
    @staticmethod
    def clicked(boss):
        global _opts, _minim
        _opts = boss.opts
        curr = _curr()

        dialog = get_export_dialog()

        filename = None
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.chooser.get_filename()
        # No destruir el dialogo (destroy() crashea en GTK3/WSLg): ocultar y
        # reutilizar la instancia. Vease get_export_dialog / HelpWindow.
        dialog.hide()

        if filename is None or filename == '':
            return
        filename = ajusta_extension(filename, dialog)

        w = int(_opts.hsize)
        h = int(_opts.vsize)
        if curr.curr_op in ['compo_one', 'compo_two']:
            w = 800
            h = 1100
        _minim = min(w, h)
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr = cairo.Context(surface)
        cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        cr.rectangle(0, 0, w, h)
        cr.fill()
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.set_line_width(float(_opts.base))
        dr = DrawMixin(_opts, DrawPng())
        dr.dispatch_pres(cr, w, h)
        if _opts.labels == 'true' or curr.curr_op in ['compo_one', 'compo_two']:
            draw_label(cr, w, h)

        # Convertir ARGB (Cairo) a RGBA (PIL) intercambiando bytes
        s = surface
        buf = bytes(s.get_data())
        ba = bytearray(len(buf))
        for i in range(0, len(buf), 4):
            ba[i] = buf[i + 2]
            ba[i + 1] = buf[i + 1]
            ba[i + 2] = buf[i]
            ba[i + 3] = buf[i + 3]

        im = PIL.Image.frombuffer("RGBA", (s.get_width(), s.get_height()), bytes(ba), "raw", "RGBA", 0, 1)
        res = int(_opts.resolution)
        im.info['dpi'] = (res, res)
        guardar_imagen(im, filename)

        viewer = getattr(_opts, 'pngviewer', None)
        if viewer:
            try:
                subprocess.Popen(shlex.split(viewer) + [filename],
                                 stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL,
                                 start_new_session=True)
            except (OSError, FileNotFoundError):
                pass

    @staticmethod
    def simple_batch(table="plagram"):
        global _opts
        boss = _boss()
        curr = _curr()
        _opts = boss.opts
        w = 1280
        h = 1020
        folder = os.path.expanduser("~")
        curr.curr_op = "draw_planetogram"
        chlist = curr.datab.get_chartlist(table)
        chart = curr.curr_chart

        for id, name, sur in chlist:
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
            cr = cairo.Context(surface)
            cr.set_source_rgb(1.0, 1.0, 1.0)
            cr.rectangle(0, 0, w, h)
            cr.fill()
            cr.set_line_join(cairo.LINE_JOIN_ROUND)
            cr.set_line_width(float(_opts.base))
            dr = DrawMixin(_opts, DrawPng())
            curr.datab.load_chart(table, id, chart)
            dr.dispatch_pres(cr, w, h)
            wname = "_".join([name, sur, "pg"])
            filename = ".".join([wname, 'png'])
            filename = os.path.join(folder, filename)
            surface.write_to_png(filename)


def _layout(cr, font_str, size):
    layout = PangoCairo.create_layout(cr)
    font = Pango.FontDescription.from_string(font_str)
    font.set_size(int(size * Pango.SCALE))
    layout.set_font_description(font)
    return layout


def draw_label(cr, w, h):
    cr.identity_matrix()
    curr = _curr()
    clickops = ['click_hh', 'click_nn', 'click_bridge', 'click_nh', 'click_rr',
                'click_ss', 'click_rs', 'click_sn', 'ascent_star', 'wundersensi_star',
                'polar_star', 'paarwabe_plot', 'crown_comp',
                'dyn_cuad2', 'click_hn', 'subject_click']
    sheetopts = ['dat_nat', 'dat_nod', 'dat_house', 'prog_nat', 'prog_nod',
                 'prog_local', 'prog_soul']

    if curr.curr_op in clickops or (curr.clickmode == 'click' and curr.opmode != 'simple'):
        d_name(cr, w, h, kind='click')
    elif curr.curr_op in ['compo_one', 'compo_two']:
        compo_name(cr, w, h)
    elif curr.curr_op not in sheetopts:
        d_name(cr, w, h)


def compo_name(cr, w, h):
    curr = _curr()
    layout = _layout(cr, _opts.font, int(7 * _minim * 0.9 * MAGICK_SCALE))
    h *= 0.995
    mastcol = (0.8, 0, 0.1)
    clickcol = (0, 0, 0.4)
    mastname = "%s %s" % (curr.curr_chart.first, curr.curr_chart.last)
    clickname = "%s %s" % (curr.curr_click.first, curr.curr_click.last)
    cr.set_source_rgb(*mastcol)
    layout.set_alignment(Pango.Alignment.RIGHT)
    layout.set_text(clickname, -1)
    _, logical = layout.get_extents()
    xpos = logical.width / Pango.SCALE
    ypos = logical.height / Pango.SCALE
    cr.move_to(w - xpos - 30, h - ypos)
    PangoCairo.show_layout(cr, layout)
    cr.set_source_rgb(*clickcol)
    layout.set_alignment(Pango.Alignment.LEFT)
    layout.set_text(mastname, -1)
    cr.move_to(30, h - ypos)
    PangoCairo.show_layout(cr, layout)


def d_name(cr, w, h, kind='radix'):
    curr = _curr()
    layout = _layout(cr, _opts.font, int(6 * _minim * MAGICK_SCALE))
    h *= 0.995

    mastcol = (0, 0, 0.4)
    clickcol = (0.8, 0, 0.1)
    mastname = "%s %s" % (curr.curr_chart.first, curr.curr_chart.last)
    clickname = "%s %s" % (curr.curr_click.first, curr.curr_click.last)

    if kind == "click":
        mastcol, clickcol = clickcol, mastcol
        mastname, clickname = clickname, mastname
        date, time = parsestrtime(curr.curr_click.date)
        date = date + " " + time.split(" ")[0]
        geodat = curr.format_longitud(kind='click') + " " + curr.format_latitud(kind='click')
        loc = curr.curr_click.city + " (" + t(curr.curr_chart.country)[0] + ") "
        text = "\n" + date + "\n" + loc + geodat
    else:
        date, time = parsestrtime(curr.curr_chart.date)
        date = date + " " + time.split(" ")[0]
        geodat = curr.format_longitud() + " " + curr.format_latitud()
        loc = curr.curr_chart.city + " (" + t(curr.curr_chart.country)[0] + ") "
        text = "\n" + date + "\n" + loc + geodat

    cr.set_source_rgb(*mastcol)
    layout.set_alignment(Pango.Alignment.RIGHT)
    layout.set_text(mastname + text, -1)
    _, logical = layout.get_extents()
    xpos = logical.width / Pango.SCALE
    ypos = logical.height / Pango.SCALE
    cr.move_to(w - xpos - 5, h - ypos)
    PangoCairo.show_layout(cr, layout)

    if kind == 'click':
        cr.set_source_rgb(*clickcol)
        layout.set_alignment(Pango.Alignment.LEFT)
        date, time = parsestrtime(curr.curr_chart.date)
        date = date + " " + time.split(" ")[0]
        geodat = curr.format_longitud() + " " + curr.format_latitud()
        loc = curr.curr_chart.city + " (" + t(curr.curr_chart.country)[0] + ") "
        text = "\n" + date + "\n" + loc + geodat
        layout.set_text(clickname + text, -1)
        cr.move_to(5, h - ypos)
        PangoCairo.show_layout(cr, layout)
