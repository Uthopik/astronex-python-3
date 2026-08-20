# -*- coding: utf-8 -*-
import sys
import os
import re
import pickle

from gi.repository import Gtk, Gdk

from astronex.extensions.path import path
from astronex.gui.searchview import SearchView


def _boss():
    from astronex.boss import boss
    return boss


def _curr():
    return _boss().get_state()


def _combo_text(combo):
    it = combo.get_active_iter()
    if it is not None:
        return combo.get_model()[it][0]
    child = combo.get_child()
    if child is not None:
        return child.get_text()
    return ""


regex = re.compile(r"[A-Za-z][_A-Za-z0-9]*$")


class MixerPanel(Gtk.Box):
    TARGETS = [
        Gtk.TargetEntry.new('MY_TREE_MODEL_ROW', Gtk.TargetFlags.SAME_WIDGET, 0),
        Gtk.TargetEntry.new('text/plain', 0, 1),
        Gtk.TargetEntry.new('TEXT', 0, 2),
        Gtk.TargetEntry.new('STRING', 0, 3),
    ]

    def __init__(self, parent):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.HORIZONTAL)
        boss = _boss()
        self.boss = boss
        self.views = {}
        self.menus = {}
        self.clip = None
        self.changes = False

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        selector = self.make_tables_selector()
        hbox.pack_start(selector, False, False, 0)
        hbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_border_width(6)
        button = Gtk.RadioButton.new_with_label_from_widget(None, _('Copiar'))
        button.action = 'copy'
        button.connect('toggled', self.on_action_toggled)
        vbox.pack_start(button, False, False, 0)
        button2 = Gtk.RadioButton.new_with_label_from_widget(button, _('Mover'))
        button2.action = 'move'
        button2.connect('toggled', self.on_action_toggled)
        vbox.pack_start(button2, False, False, 0)
        align = Gtk.Alignment(xalign=0.5, yalign=0.5)
        align.add(vbox)
        hbox.pack_start(align, False, False, 0)
        hbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)

        selector = self.make_tables_selector()
        hbox.pack_start(selector, False, False, 0)

        frame = Gtk.Frame()
        frame.add(hbox)
        frame.set_border_width(6)
        self.pack_start(frame, False, False, 0)

        adminpanel = self.make_admin_panel()
        self.pack_start(adminpanel, False, False, 0)

    def make_tables_selector(self):
        curr = _curr()
        boss = _boss()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        liststore = Gtk.ListStore(str)
        tables = Gtk.ComboBox.new_with_model_and_entry(liststore)
        tables.set_entry_text_column(0)
        tables.set_size_request(182, -1)
        tables.get_child().set_editable(False)
        tablelist = curr.datab.get_databases()

        for c in tablelist:
            liststore.append([c])
        index = 0
        for i, r in enumerate(liststore):
            if r[0] == curr.database:
                index = i
                break
        tables.set_active(index)

        but = Gtk.Button()
        img = Gtk.Image()
        appath = boss.app.appath
        imgfile = path.joinpath(appath, "astronex/resources/refresh-18.png")
        img.set_from_file(str(imgfile))
        but.set_image(img)
        but.connect('clicked', self.on_refresh_clicked, tables)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.pack_start(tables, False, False, 0)
        hbox.pack_start(but, False, False, 0)
        vbox.pack_start(hbox, False, False, 0)

        chartmodel = Gtk.ListStore(str, int)
        chartview = SearchView(chartmodel)
        selection = chartview.get_selection()
        selection.set_mode(Gtk.SelectionMode.SINGLE)
        chartlist = curr.datab.get_chartlist(_combo_text(tables))

        for c in chartlist:
            glue = ", "
            if c[2] == '':
                glue = ''
            chartmodel.append([c[2] + glue + c[1], int(c[0])])

        cell = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(None, cell, text=0)
        chartview.append_column(column)
        chartview.set_headers_visible(False)
        sel = chartview.get_selection()
        sel.set_mode(Gtk.SelectionMode.SINGLE)
        sel.select_path(Gtk.TreePath.new_from_indices([0]))

        menu = Gtk.Menu()
        menu_item = Gtk.MenuItem(label=_('Eliminar'))
        menu.append(menu_item)
        menu_item.op = 'delete'
        menu_item.connect("activate", self.on_menuitem_activate, chartview)
        menu_item.show()
        menu_item = Gtk.MenuItem(label=_('Deshacer'))
        menu.append(menu_item)
        menu_item.op = 'undo'
        menu_item.connect("activate", self.on_menuitem_activate, chartview)
        menu_item.show()
        chartview.connect("button-press-event", self.on_view_clicked, menu)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.add(chartview)
        vbox.pack_start(sw, True, True, 0)
        tables.connect('changed', self.on_tables_changed, chartview)
        vbox.set_size_request(210, -1)

        chartview.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK,
                                           self.TARGETS,
                                           Gdk.DragAction.COPY)
        chartview.enable_model_drag_dest(self.TARGETS, Gdk.DragAction.DEFAULT)

        chartview.connect("drag-data-get", self.drag_data_get_data)
        chartview.connect("drag-data-received", self.drag_data_received_data)
        chartview.connect("row-activated", self.on_row_activated)
        self.views[chartview] = tables

        return vbox

    def on_action_toggled(self, but):
        action_name = getattr(but, 'action', 'copy')
        action = [Gdk.DragAction.COPY, Gdk.DragAction.MOVE][action_name == 'move']
        for view in self.views:
            view.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK, self.TARGETS, action)
            view.enable_model_drag_dest(self.TARGETS, action)

    def on_row_activated(self, view, path_, col):
        table = _combo_text(self.views[view])
        parent = self.get_parent()
        parent.set_current_page(0)
        combo = parent.get_nth_page(0).tables
        model = combo.get_model()
        it = model.get_iter_first()
        index = 0
        while it:
            if model.get_value(it, 0) == table:
                index = int(model.get_path(it)[0])
                break
            it = model.iter_next(it)
        combo.set_active(index)
        m, i = view.get_selection().get_selected()
        if not i:
            return
        try:
            first, last = m.get_value(i, 0).split(',')
        except ValueError:
            return
        parent.get_nth_page(0).findchart(first, last)

    def on_view_clicked(self, view, event, menu):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            x = int(event.x)
            y = int(event.y)
            pthinfo = view.get_path_at_pos(x, y)
            if pthinfo is not None:
                p, col, cellx, celly = pthinfo
                view.grab_focus()
                view.set_cursor(p, col, False)
                if self.clip is None:
                    menu.get_children()[1].set_sensitive(False)
                else:
                    menu.get_children()[1].set_sensitive(True)
                menu.popup_at_pointer(event)
            return True

    def on_menuitem_activate(self, menuitem, view):
        curr = _curr()
        op = getattr(menuitem, 'op', None)
        table = self.views[view]
        tablename = _combo_text(table)
        if op == 'delete':
            model, it = view.get_selection().get_selected()
            if not it:
                return
            id = model.get_value(it, 1)
            chart = curr.newchart()
            curr.datab.load_chart(tablename, id, chart)
            self.clip = chart
            if not self.safe_delete(tablename, id):
                return
            curr.datab.delete_chart(tablename, id)
            model.remove(it)
        elif op == 'undo' and self.clip:
            rowid = self.new_chart(self.clip, tablename)
            if rowid:
                model, it = view.get_selection().get_selected()
                row = [", ".join([self.clip.last, self.clip.first]), rowid]
                p = model.get_path(it)
                model.insert(int(p[0]), row)
                self.clip = None
        self.changes = True

    def on_refresh_clicked(self, but, combo):
        combo.emit('changed')

    def on_tables_changed(self, combo, chartview):
        curr = _curr()
        if combo.get_active() == -1:
            return
        if chartview:
            chartmodel = Gtk.ListStore(str, int)
            chartlist = curr.datab.get_chartlist(_combo_text(combo))
            for c in chartlist:
                glue = ", "
                if not c[2]:
                    glue = ''
                chartmodel.append([c[2] + glue + c[1], int(c[0])])
            chartview.set_model(chartmodel)
            chartview.get_selection().select_path(Gtk.TreePath.new_from_indices([0]))
            self.views[chartview] = combo

    def drag_data_get_data(self, treeview, context, selection, target_id, etime):
        treeselection = treeview.get_selection()
        model, it = treeselection.get_selected()
        data = ";".join([model.get_value(it, 0), str(model.get_value(it, 1))])
        selection.set(selection.get_target(), 8, data.encode('utf-8'))

    def drag_data_received_data(self, treeview, context, x, y, selection, info, etime):
        curr = _curr()
        mytab = othertab = ''
        for key in self.views.keys():
            if key == treeview:
                mytab = _combo_text(self.views[key])
            else:
                othertab = _combo_text(self.views[key])
        if mytab == othertab:
            return
        model = treeview.get_model()
        raw = selection.get_data()
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8')
        data = raw.split(";")
        srcid = int(data[-1])

        chart = curr.newchart()
        curr.datab.load_chart(othertab, srcid, chart)
        id = self.new_chart(chart, mytab)
        if not id:
            return
        data[-1] = id

        drop_info = treeview.get_dest_row_at_pos(x, y)
        if drop_info:
            p, position = drop_info
            it = model.get_iter(p)
            if (position == Gtk.TreeViewDropPosition.BEFORE
                    or position == Gtk.TreeViewDropPosition.INTO_OR_BEFORE):
                model.insert_before(it, data)
            else:
                model.insert_after(it, data)
        else:
            model.append(data)

        self.changes = True
        if context.get_actions() & Gdk.DragAction.MOVE:
            context.finish(True, True, etime)
            if not self.safe_delete(othertab, srcid):
                return
            curr.datab.delete_chart(othertab, srcid)

    def constrainterror_dlg(self, fi, la):
        msg = _("Una carta con este nombre: %s %s existe. Sobrescribir?") % (fi, la)
        dialog = Gtk.MessageDialog(transient_for=None, modal=True,
                                   message_type=Gtk.MessageType.WARNING,
                                   buttons=Gtk.ButtonsType.OK_CANCEL,
                                   text=msg)
        result = dialog.run()
        dialog.hide()
        return result

    def new_chart(self, chart, table):
        curr = _curr()
        from sqlite3 import DatabaseError
        try:
            lastrow = curr.datab.store_chart(table, chart)
        except DatabaseError:
            result = self.constrainterror_dlg(chart.first, chart.last)
            if result != Gtk.ResponseType.OK:
                return None
            curr.datab.delete_chart_from_name(table, chart.first, chart.last)
            lastrow = curr.datab.store_chart(table, chart)
            curr.fix_couples(table, chart.first, chart.last, lastrow)
        return lastrow

    def make_admin_panel(self):
        boss = _boss()
        appath = boss.app.appath
        thebox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox = Gtk.ButtonBox(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_layout(Gtk.ButtonBoxStyle.SPREAD)
        vbox.set_border_width(3)

        for icon_name, label_text, callback in [
            ("gtk-new-18.png", _('_Crear tabla'), self.on_create_table),
            ("stock_delete.png", _('E_liminar tabla'), self.on_delete_table),
            ("folder-convert24.png", _('_Renombrar'), self.on_rename_table),
        ]:
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            img = Gtk.Image()
            imgfile = path.joinpath(appath, "astronex/resources/" + icon_name)
            img.set_from_file(str(imgfile))
            hbox.pack_start(img, True, True, 0)
            but = Gtk.Button.new_with_mnemonic(label_text)
            but.connect('clicked', callback)
            hbox.pack_start(but, True, True, 0)
            vbox.pack_start(hbox, False, False, 0)

        frame = Gtk.Frame()
        frame.set_border_width(6)
        frame.add(vbox)
        thebox.pack_start(frame, True, True, 0)

        vbox = Gtk.ButtonBox(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_layout(Gtk.ButtonBoxStyle.SPREAD)
        vbox.set_border_width(3)

        for icon_name, label_text, callback in [
            ("gtk-save.png", _('_Exportar  tabla'), self.on_table_export),
            ("import.png", _('_Importar  tabla'), self.on_table_import),
        ]:
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            img = Gtk.Image()
            imgfile = path.joinpath(appath, "astronex/resources/" + icon_name)
            img.set_from_file(str(imgfile))
            hbox.pack_start(img, True, True, 0)
            but = Gtk.Button.new_with_mnemonic(label_text)
            but.connect('clicked', callback)
            hbox.pack_start(but, True, True, 0)
            vbox.pack_start(hbox, False, False, 0)

        frame = Gtk.Frame()
        frame.set_border_width(6)
        frame.add(vbox)
        thebox.pack_start(frame, True, True, 0)
        return thebox

    def check_name(self, name):
        ok = regex.match(name)
        if not ok:
            msg = [_("El nombre de las tablas solo puede comenzar con"),
                   _("'_' o letra*, seguida de letra*, numero o '_'."),
                   _("* A-Z, a-z, sin tildes ni caracteres compuestos")]
            self.messagedialog("\n".join(msg))
        return ok

    def on_create_table(self, but):
        entry = Gtk.Entry()
        dialog = Gtk.Dialog(title=_("Nombre:"),
                            parent=None,
                            modal=True, destroy_with_parent=True)
        dialog.add_buttons(_("_Cancelar"), Gtk.ResponseType.NONE,
                           _("_OK"), Gtk.ResponseType.OK)
        dialog.get_content_area().pack_end(entry, True, True, 0)
        entry.grab_focus()
        dialog.connect("response", self.create_response)
        dialog.show_all()

    def create_response(self, dialog, rid):
        curr = _curr()
        if rid == Gtk.ResponseType.NONE or rid == Gtk.ResponseType.DELETE_EVENT:
            dialog.hide()
            return
        tablelist = curr.datab.get_databases()
        new = dialog.get_content_area().get_children()[0].get_text()
        if not self.check_name(new):
            return
        if new in tablelist:
            result = self.replacedialog(new)
            if result != Gtk.ResponseType.OK:
                return
        curr.datab.create_table(new)
        self.relist(new)
        dialog.hide()

    def replacedialog(self, tbl):
        msg = _("La tabla %s existe. Reemplazarla, perdiendo los datos?") % tbl
        dialog = Gtk.MessageDialog(transient_for=None, modal=True,
                                   message_type=Gtk.MessageType.WARNING,
                                   buttons=Gtk.ButtonsType.OK_CANCEL,
                                   text=msg)
        result = dialog.run()
        dialog.hide()
        return result

    def relist(self, new):
        curr = _curr()
        liststore = Gtk.ListStore(str)
        tablelist = curr.datab.get_databases()
        for c in tablelist:
            liststore.append([c])
        index = 0
        for i, r in enumerate(liststore):
            if r[0] == new:
                index = i
                break
        table = None
        for key in self.views.keys():
            table = self.views[key]
            table.set_model(liststore)
        if table is not None:
            table.set_active(index)
        self.changes = True

    def on_delete_table(self, but):
        curr = _curr()
        dialog = Gtk.Dialog(title=_("Eliminar tabla"),
                            parent=None,
                            modal=True, destroy_with_parent=True)
        dialog.add_buttons(_("_Cancelar"), Gtk.ResponseType.NONE,
                           _("_OK"), Gtk.ResponseType.OK)
        liststore = Gtk.ListStore(str)
        tables = Gtk.ComboBox.new_with_model_and_entry(liststore)
        tables.set_entry_text_column(0)
        tables.set_size_request(250, -1)
        tables.get_child().set_editable(False)
        tablelist = curr.datab.get_databases()
        for c in tablelist:
            liststore.append([c])
        tables.set_active(0)
        dialog.get_content_area().pack_start(tables, True, True, 0)
        dialog.connect("response", self.delete_response)
        dialog.show_all()

    def delete_response(self, dialog, rid):
        boss = _boss()
        curr = _curr()
        if rid == Gtk.ResponseType.NONE or rid == Gtk.ResponseType.DELETE_EVENT:
            dialog.hide()
            return
        combo = dialog.get_content_area().get_children()[0]
        tbl = _combo_text(combo)
        if tbl == boss.opts.database or tbl == boss.opts.favourites:
            self.messagedialog(_("No puedo eliminar una tabla predeterminada."))
            return
        if not self.safe_delete_table(tbl):
            return
        result = self.deletedialog(tbl)
        if result == Gtk.ResponseType.OK:
            curr.datab.delete_table(tbl)
            self.relist('')
            dialog.hide()

    def messagedialog(self, msg):
        dialog = Gtk.MessageDialog(transient_for=None, modal=True,
                                   message_type=Gtk.MessageType.INFO,
                                   buttons=Gtk.ButtonsType.OK,
                                   text=msg)
        dialog.run()
        dialog.hide()

    def deletedialog(self, tbl):
        msg = _("Desea realmente eliminar la tabla %s?") % tbl
        dialog = Gtk.MessageDialog(transient_for=None, modal=True,
                                   message_type=Gtk.MessageType.WARNING,
                                   buttons=Gtk.ButtonsType.OK_CANCEL,
                                   text=msg)
        result = dialog.run()
        dialog.hide()
        return result

    def on_rename_table(self, but):
        curr = _curr()
        dialog = Gtk.Dialog(title=_("Cambiar nombre"),
                            parent=None,
                            modal=True, destroy_with_parent=True)
        dialog.add_buttons(_("_Cancelar"), Gtk.ResponseType.NONE,
                           _("_OK"), Gtk.ResponseType.OK)
        liststore = Gtk.ListStore(str)
        tables = Gtk.ComboBox.new_with_model_and_entry(liststore)
        tables.set_entry_text_column(0)
        tables.set_size_request(250, -1)
        tables.get_child().set_editable(False)
        tablelist = curr.datab.get_databases()
        for c in tablelist:
            liststore.append([c])
        tables.set_active(0)
        dialog.get_content_area().pack_start(tables, True, True, 0)
        entry = Gtk.Entry()
        entry.set_text(_combo_text(tables))
        dialog.get_content_area().pack_start(entry, True, True, 0)
        tables.connect('changed', self.on_renamecombo_changed, entry)
        dialog.connect("response", self.rename_response)
        dialog.show_all()

    def on_renamecombo_changed(self, combo, entry):
        entry.set_text(_combo_text(combo))

    def rename_response(self, dialog, rid):
        boss = _boss()
        curr = _curr()
        if rid == Gtk.ResponseType.NONE or rid == Gtk.ResponseType.DELETE_EVENT:
            dialog.hide()
            return
        children = dialog.get_content_area().get_children()
        oldname = _combo_text(children[0])
        newname = children[1].get_text()
        if oldname == boss.opts.database or oldname == boss.opts.favourites:
            self.messagedialog(_("No puedo cambiar el nombre a una tabla predeterminada."))
            return
        if not self.safe_delete_table(oldname):
            return
        if not self.check_name(newname):
            return
        curr.datab.rename_chart(oldname, newname)
        self.relist(newname)
        dialog.hide()

    def on_table_export(self, but):
        curr = _curr()
        dialog = Gtk.Dialog(title=_("Exportar tabla"),
                            parent=None,
                            modal=True, destroy_with_parent=True)
        dialog.add_buttons(_("_Cancelar"), Gtk.ResponseType.NONE,
                           _("_OK"), Gtk.ResponseType.OK)
        liststore = Gtk.ListStore(str)
        tables = Gtk.ComboBox.new_with_model_and_entry(liststore)
        tables.set_entry_text_column(0)
        tables.set_size_request(250, -1)
        tables.get_child().set_editable(False)
        tablelist = curr.datab.get_databases()
        for c in tablelist:
            liststore.append([c])
        tables.set_active(0)
        dialog.get_content_area().pack_start(tables, True, True, 0)
        dialog.connect("response", self.export_response)
        dialog.show_all()

    def export_response(self, dialog, rid):
        curr = _curr()
        if rid == Gtk.ResponseType.NONE or rid == Gtk.ResponseType.DELETE_EVENT:
            dialog.hide()
            return
        table = _combo_text(dialog.get_content_area().get_children()[0])

        folder = os.path.expanduser("~") + os.path.sep
        name = folder + table + ".nxt"
        export = []

        chartlist = curr.datab.get_chartlist(table)
        for c in chartlist:
            id = int(c[0])
            chart = curr.newchart()
            curr.datab.load_chart(table, id, chart)
            export.append(chart)

        with open(name, 'wb') as f:
            pickle.dump(export, f, -1)
        dialog.hide()

    def on_table_import(self, but):
        dialog = Gtk.Dialog(title=_("Importar tabla"),
                            parent=None,
                            modal=True, destroy_with_parent=True)
        dialog.add_buttons(_("_Cancelar"), Gtk.ResponseType.NONE,
                           _("_OK"), Gtk.ResponseType.OK)

        table = Gtk.Table(n_rows=2, n_columns=3, homogeneous=False)
        table.set_col_spacings(3)
        lbl = Gtk.Label(label=_('Archivo'))
        table.attach(lbl, 0, 1, 0, 1)
        entry = Gtk.Entry()
        table.attach(entry, 1, 2, 0, 1)
        but = Gtk.Button(label=_('Examinar'))
        table.attach(but, 2, 3, 0, 1)
        tname = Gtk.Label(label=_('Tabla'))
        table.attach(tname, 0, 1, 1, 2)
        tentry = Gtk.Entry()
        table.attach(tentry, 1, 2, 1, 2)
        info = Gtk.Label()
        table.attach(info, 2, 3, 1, 2)
        dialog.get_content_area().pack_start(table, False, False, 0)
        but.connect('clicked', self.on_filebrowse, entry, tentry)

        dialog.connect("response", self.import_response, entry, tentry, info)
        dialog.show_all()

    def import_response(self, dialog, rid, entry, tentry, info):
        curr = _curr()
        if rid == Gtk.ResponseType.NONE or rid == Gtk.ResponseType.DELETE_EVENT:
            dialog.hide()
            return
        elif rid == Gtk.ResponseType.OK:
            name = tentry.get_text()
            if not self.check_name(name):
                return
            tablelist = curr.datab.get_databases()
            if name in tablelist:
                result = self.replacedialog(name)
                if result != Gtk.ResponseType.OK:
                    return
            filename = entry.get_text()
            try:
                with open(filename, 'rb') as f:
                    imported = pickle.load(f)
            except IOError:
                self.messagedialog(_('Error abriendo el archivo'))
                return
            except Exception:
                self.messagedialog(_('Error importando la tabla'))
                return
            curr.datab.create_table(name)
            li = len(imported)
            info.set_text('(%s)' % li)
            for i, data in enumerate(imported):
                self.new_chart(data, name)
                info.set_text(_('%s de %s') % (i, li))
                while Gtk.events_pending():
                    Gtk.main_iteration()
            self.relist('')
            dialog.hide()

    def on_filebrowse(self, but, entry, tentry):
        dialog = Gtk.FileChooserDialog(
            title="Abrir archivo...",
            parent=None,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons(_("_Cancelar"), Gtk.ResponseType.CANCEL,
                           _("_Abrir"), Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_current_folder(os.path.expanduser("~"))

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            entry.set_text(filename)
            name = os.path.basename(os.path.splitext(filename)[0])
            tentry.set_text(name)
        dialog.hide()

    def on_compact(self, but):
        _curr().datab.vacuum()

    def safe_delete(self, table, id):
        curr = _curr()
        if not curr.safe_delete_chart(table, id):
            msg = _('No puedo eliminar una carta con pareja!')
            dialog = Gtk.MessageDialog(transient_for=None, modal=True,
                                       message_type=Gtk.MessageType.WARNING,
                                       buttons=Gtk.ButtonsType.OK,
                                       text=msg)
            dialog.run()
            dialog.hide()
            return False
        return True

    def safe_delete_table(self, table):
        curr = _curr()
        if not curr.safe_delete_table(table):
            msg = _('No puedo eliminar una tabla con pareja!')
            dialog = Gtk.MessageDialog(transient_for=None, modal=True,
                                       message_type=Gtk.MessageType.WARNING,
                                       buttons=Gtk.ButtonsType.OK,
                                       text=msg)
            dialog.run()
            dialog.hide()
            return False
        return True
