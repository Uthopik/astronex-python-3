# -*- coding: utf-8 -*-
import os
import sys
import shlex
import subprocess
from math import pi as PI
from datetime import datetime

import cairo
from gi.repository import Gtk, Pango, PangoCairo

from astronex.drawing.dispatcher import DrawMixin
from astronex.gui.plagram_dlg import PgMixin
from astronex.drawing.datasheets import labels as _datasheets_labels  # noqa: F401
from astronex.utils import parsestrtime


def _boss():
    from astronex.boss import boss
    return boss


def _curr():
    return _boss().get_state()


PDFH = 845.04685
PDFW = 597.50787  # A4 points
pdflabels = True

papers = {
    'A3': (845.04685, 1195.0157),
    'A4': (597.50787, 845.04685),
    'A5': (421.10079, 597.50787),
    'custom': (597.50787, 597.50787),
    'custom5': (421.10079, 421.10079),
}

singles = ['draw_nat', 'draw_nod', 'draw_house', 'draw_local',
           'draw_soul', 'draw_prof', 'draw_int', 'draw_single',
           'draw_radsoul']

landscape = ['bio_nat', 'bio_nod', 'bio_soul', 'click_bridge', 'dyn_cuad',
             'rad_and_transit', 'dyn_cuad2']
special = ['click_bridge', 'rad_and_transit']
sheets = ['dat_nat', 'dat_house', 'dat_node',
          'prog_nat', 'prog_nod', 'prog_local', 'prog_soul']


def _layout(cr, font_str, size):
    layout = PangoCairo.create_layout(cr)
    font = Pango.FontDescription.from_string(font_str)
    font.set_size(int(size * Pango.SCALE))
    layout.set_font_description(font)
    return layout


class DrawPdf(object):
    w = PDFW
    h = PDFH

    @classmethod
    def clicked(cls, boss):
        curr = _curr()
        dialog = Gtk.FileChooserDialog(
            title=_("Guardar..."),
            parent=None,
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_buttons(_("_Cancelar"), Gtk.ResponseType.CANCEL,
                           _("_Guardar"), Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.OK)

        filt = Gtk.FileFilter()
        filt.set_name(_("Documento PDF"))
        filt.add_mime_type("application/pdf")
        filt.add_pattern("*.pdf")
        dialog.add_filter(filt)
        name = cls.format_name()
        dialog.set_current_name(name)
        dialog.set_current_folder(os.path.expanduser("~"))
        dialog.set_do_overwrite_confirmation(True)

        filename = None
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
        # No destruir el dialogo (destroy() de una toplevel tras run() crashea en
        # GTK3/WSLg): ocultar. GTK retiene la instancia oculta; no se segfaultea.
        dialog.hide()

        if not filename:
            return

        surface = cls.dispatch(filename)
        surface.finish()

        viewer = getattr(boss.opts, 'pdfviewer', None)
        if viewer:
            try:
                subprocess.Popen(shlex.split(viewer) + [filename],
                                 stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL,
                                 start_new_session=True)
            except (OSError, FileNotFoundError):
                pass

    @classmethod
    def dispatch(cls, filename, labels=True):
        boss = _boss()
        curr = _curr()
        opts = boss.opts
        w = PDFW
        h = PDFH
        if curr.opmode != 'simple' or curr.curr_op in landscape:
            w, h = h, w
        surface = cairo.PDFSurface(filename, w, h)
        surface.set_fallback_resolution(300, 300)
        cr = cairo.Context(surface)
        cr.rectangle(0, 0, w, h)
        cr.clip()
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.rectangle(0, 0, w, h)
        cr.fill()
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.set_line_width(float(opts.base))
        dr = DrawMixin(opts, cls())
        if curr.opmode == 'double' or curr.curr_op in special:
            w *= 0.93
            cr.translate((PDFH - w) / 2, 0.0)
        elif curr.opmode == 'triple':
            h *= 0.95
            cr.translate(0.0, (PDFW - h) / 2)
        elif curr.opmode == 'simple':
            if curr.curr_op.startswith('bio'):
                w *= 0.9
                h *= 0.9
                cr.translate((PDFH - w) / 2, (PDFW - h) / 2)
            elif curr.curr_op.startswith('dyn_c'):
                h *= 0.9
                w *= 0.8
                cr.translate((PDFH - w) / 2, (PDFW - h))
            elif curr.curr_op == 'dyn_stars':
                h *= 0.7
                w *= 0.95
                cr.translate((PDFW - w) / 2, (PDFH - h) / 3)
            elif curr.curr_op.startswith('subjec'):
                h *= 0.9
                w *= 0.9
                cr.translate((PDFH - w) / 10, 0.0)
            elif curr.curr_op == 'click_counterpanel':
                h *= 0.75
                cr.translate(0.0, (PDFH - h) / 3)
            elif curr.curr_op in ['compo_one', 'compo_two']:
                h *= 0.9
                cr.translate(0.0, (PDFH - h) / 3)
            elif curr.curr_op == 'polar_star':
                h *= 0.8
                w *= 0.9
                cr.translate((PDFW - w) / 2, (PDFH - h) / 3)
            else:
                h *= 0.9
        cls.w = w
        cls.h = h
        dr.dispatch_pres(cr, w, h)
        if curr.curr_op not in sheets and pdflabels:
            cls.d_pdf_labels(cr, w, h)
        elif curr.curr_op in ['dat_nat', 'dat_house', 'dat_node']:
            cls.d_pdf_header(cr, w, h, sheet=True)
        cr.show_page()
        return surface

    @classmethod
    def format_name(cls):
        boss = _boss()
        curr = _curr()
        suffixes = boss.suffixes
        if curr.opmode == 'simple':
            suffix = "".join([suffixes.get(curr.curr_op, 'rx'), '.pdf'])
        else:
            suffix = "".join([suffixes.get(curr.opleft, 'rx')[0],
                              suffixes.get(curr.opright, 'rx')[0]])
            d_o_t = [2, 3][curr.opmode == 'triple']
            suffix = "".join([suffix, str(d_o_t), '.pdf'])

        if curr.clickmode == 'click':
            names = [n.replace(' ', '_') for n in [curr.curr_chart.first, curr.curr_click.first]]
        else:
            names = [curr.curr_chart.first.replace(' ', '_')]
        names.append(suffix)
        return "_".join(names)

    @classmethod
    def d_pdf_header(cls, cr, w, h, sheet=False):
        boss = _boss()
        opts = boss.opts
        date = datetime.now().strftime("%d/%m/%Y")
        layout = _layout(cr, opts.font, 8)
        layout.set_text("Astro-Nex %s" % boss.get_version(), -1)
        cr.set_source_rgb(0.2, 0, 0.9)
        if sheet:
            cr.move_to(50, h + 20)
        else:
            cr.move_to(40, 40)
        PangoCairo.show_layout(cr, layout)
        layout.set_text(date, -1)
        if sheet:
            cr.move_to(w - 110, h + 20)
        else:
            cr.move_to(w - 90, 40)
        PangoCairo.show_layout(cr, layout)

    @classmethod
    def d_pdf_labels(cls, cr, w, h):
        boss = _boss()
        curr = _curr()
        opts = boss.opts
        cr.set_source_rgb(0.2, 0, 0.9)
        cr.identity_matrix()

        opmode = curr.opmode
        curr_op = curr.curr_op

        layout = _layout(cr, opts.font, 8)
        date, time = parsestrtime(curr.curr_chart.date)
        date = date + " " + time.split(" ")[0]
        geodat = curr.format_longitud() + " " + curr.format_latitud()
        name = curr.curr_chart.first + " " + curr.curr_chart.last
        if opmode == 'simple' and curr_op == 'draw_local':
            loc = curr.curr_chart.city + " (" + t(curr.curr_chart.country) + ")"
        else:
            loc = curr.curr_chart.city + " (" + t(curr.curr_chart.country) + ")"

        glue = " " if (opmode == 'simple' and (curr_op.startswith('bio') or curr_op.startswith('dyn_c'))) else "\n"
        label_text = name + glue + date + glue + loc + glue + geodat
        layout.set_text(label_text, -1)
        _, logical = layout.get_extents()
        xpos = logical.width / Pango.SCALE
        cr.move_to(40, 50)
        PangoCairo.show_layout(cr, layout)

        cls.d_pdf_header(cr, w, h)
