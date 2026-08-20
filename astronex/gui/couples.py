# -*- coding: utf-8 -*-
import re
from datetime import datetime, timezone

from gi.repository import Gtk, Gdk

from astronex.gui.datewidget import DateEntry, set_background
from astronex.extensions.validation import ValidationError
from astronex.extensions.path import path


def _boss():
    from astronex.boss import boss
    return boss


def _curr():
    return _boss().get_state()


regex = re.compile(r"[A-Za-z][_A-Za-z0-9]*$")


def _combo_text(combo):
    it = combo.get_active_iter()
    if it is not None:
        return combo.get_model()[it][0]
    child = combo.get_child()
    if child is not None:
        return child.get_text()
    return ""


class CouplesPanel(Gtk.Box):

    def __init__(self, parent):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.HORIZONTAL)
        boss = _boss()
        curr = _curr()
        self.boss = boss
        self.data = {'ftab': '', 'mtab': '', 'fname': '', 'mname': '', 'fid': None, 'mid': None}
        self.changes = False
        self.coup_ix = 0
        # El dialogo "Crear pareja" se retiene y se reutiliza OCULTO (hide) en
        # lugar de destruirlo: destruir un Gtk.Dialog con ESC en GTK3/WSLg
        # provocaba un segfault que mataba toda la app. Al no destruirlo nunca
        # durante la sesion se evita ese camino de finalizacion (mismo patron
        # que HelpWindow en quickhelp.py).
        self.create_dialog = None

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_border_width(3)
        vbox.set_size_request(400, -1)

        button = Gtk.Button(label=_('Crear pareja'))
        button.connect('clicked', self.on_createcouple_clicked)
        vbox.pack_start(button, False, False, 0)

        coupmodel = Gtk.ListStore(str, str, int, str, str, int)
        coupview = Gtk.TreeView(model=coupmodel)
        for c in curr.couples:
            coupmodel.append([c['fem'][0], c['fem'][1], c['fem'][2],
                              c['mas'][0], c['mas'][1], c['mas'][2]])
        cell = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(None, cell, text=0)
        coupview.append_column(column)
        column = Gtk.TreeViewColumn(None, cell, text=3)
        coupview.append_column(column)
        sel = coupview.get_selection()
        sel.set_mode(Gtk.SelectionMode.SINGLE)
        sel.connect('changed', self.on_sel_changed)
        sel.select_path(Gtk.TreePath.new_from_indices([0]))
        menu = Gtk.Menu()
        menu_item = Gtk.MenuItem(label=_('Eliminar'))
        menu.append(menu_item)
        menu_item.op = 'delete'
        menu_item.connect("activate", self.on_menuitem_activate)
        coupview.connect("button-press-event", self.on_view_clicked, menu)
        menu_item.show()
        vbox.pack_start(coupview, False, False, 0)

        hbox.pack_start(vbox, True, True, 0)
        hbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_border_width(3)
        vbox.set_size_request(400, -1)
        datewid = CoupleDates(self, boss)
        dt = datetime.now()
        ld = dt.replace(tzinfo=timezone.utc)
        datewid.set_date(ld.date())
        bbox = Gtk.Alignment(xalign=0.5, yalign=0)
        bbox.add(datewid)
        vbox.pack_start(bbox, False, False, 0)
        but = Gtk.Button()
        img = Gtk.Image()
        appath = boss.app.appath
        imgfile = path.joinpath(appath, "astronex/resources/gtk-go-down.png")
        img.set_from_file(str(imgfile))
        but.set_image(img)
        but.connect('clicked', self.on_add_date_clicked)
        bbox = Gtk.Alignment(xalign=0.5, yalign=0)
        bbox.add(but)
        vbox.pack_start(bbox, False, False, 0)

        datemodel = Gtk.ListStore(str, str)
        dateview = Gtk.TreeView(model=datemodel)
        dateview.set_headers_visible(False)
        dateview.set_size_request(-1, 300)
        if curr.couples:
            for d in curr.couples[0]['dates']:
                datemodel.append([d[0], d[1]])
        cell = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(None, cell, text=0)
        dateview.append_column(column)
        cell = Gtk.CellRendererText()
        cell.set_property('editable', True)
        cell.connect('edited', self.on_cell_edited)
        column = Gtk.TreeViewColumn(None, cell, text=1)
        dateview.append_column(column)
        sel = dateview.get_selection()
        sel.set_mode(Gtk.SelectionMode.SINGLE)
        sel.select_path(Gtk.TreePath.new_from_indices([0]))
        menu = Gtk.Menu()
        menu_item = Gtk.MenuItem(label=_('Eliminar'))
        menu.append(menu_item)
        menu_item.connect("activate", self.on_menudate_activate)
        dateview.connect("button-press-event", self.on_dateview_clicked, menu)
        menu_item.show()
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.add(dateview)
        vbox.pack_start(sw, False, False, 0)

        hbox.pack_start(vbox, True, True, 0)
        frame = Gtk.Frame()
        frame.add(hbox)
        frame.set_border_width(6)
        self.pack_start(frame, False, False, 0)

        self.coupview = coupview
        self.datewid = datewid
        self.dateview = dateview
        datewid.view = dateview

    def on_createcouple_clicked(self, button):
        dialog = self.create_dialog
        if dialog is None:
            # Crear el dialogo UNA sola vez y retenerlo; nunca se destruye.
            dialog = Gtk.Dialog(
                title=_("Crear pareja"),
                parent=None,
                modal=True,
            )
            dialog.add_buttons(_("_Cancelar"), Gtk.ResponseType.NONE,
                               _("_OK"), Gtk.ResponseType.OK)
            dialog.connect("response", self.create_response)
            # No destruir con ESC ni con la X: ocultar y reutilizar.
            dialog.connect("delete-event", lambda w, e: (w.hide() or True))
            self.create_dialog = dialog
        # Reconstruir el contenido en cada apertura para refrescar las listas
        # de bases de datos / cartas (misma funcionalidad que antes).
        content = dialog.get_content_area()
        for child in content.get_children():
            content.remove(child)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.pack_start(self.make_tables_selector('f'), True, True, 0)
        hbox.pack_end(self.make_tables_selector('m'), True, True, 0)
        content.pack_start(hbox, True, True, 0)
        dialog.show_all()
        dialog.present()

    def make_tables_selector(self, key):
        curr = _curr()
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
        table = _combo_text(tables)
        self.data["%stab" % key] = table

        vbox.pack_start(tables, False, False, 0)

        chartmodel = Gtk.ListStore(str, int)
        personae = Gtk.ComboBox.new_with_model_and_entry(chartmodel)
        personae.set_entry_text_column(0)
        chartlist = curr.datab.get_chartlist(_combo_text(tables))

        for c in chartlist:
            glue = ", "
            if c[2] == '':
                glue = ''
            chartmodel.append([c[2] + glue + c[1], int(c[0])])

        personae.set_size_request(100, 28)
        personae.set_active(0)
        personae.connect('changed', self.on_persona_changed, key)
        personae.emit('changed')
        vbox.pack_start(personae, True, True, 0)
        vbox.set_size_request(210, -1)
        tables.connect('changed', self.on_tables_changed, personae, key)

        compl = Gtk.EntryCompletion()
        compl.set_text_column(0)
        compl.set_model(personae.get_model())
        personae.get_child().set_completion(compl)
        compl.connect('match-selected', self.on_person_match, personae)

        return vbox

    def on_person_match(self, compl, model, it, personae):
        sel = model.get_value(it, 0)
        for r in personae.get_model():
            if r[0] == sel:
                personae.set_active_iter(r.iter)
                break

    def on_persona_changed(self, combo, key):
        if combo.get_active() == -1:
            return
        model = combo.get_model()
        it = combo.get_active_iter()
        if it is None:
            return
        name = model.get_value(it, 0)
        try:
            last, first = name.split(',')
            name = first[1:] + " " + last
        except ValueError:
            pass
        id = model.get_value(it, 1)
        self.data["%sname" % key] = name
        self.data["%sid" % key] = id

    def on_tables_changed(self, combo, personae, key):
        curr = _curr()
        if combo.get_active() == -1:
            return
        if personae:
            chartmodel = Gtk.ListStore(str, int)
            table = _combo_text(combo)
            chartlist = curr.datab.get_chartlist(table)
            for c in chartlist:
                glue = ", "
                if not c[2]:
                    glue = ''
                chartmodel.append([c[2] + glue + c[1], int(c[0])])
            personae.set_model(chartmodel)
            personae.set_active(0)
            self.data["%stab" % key] = table

    def create_response(self, dialog, rid):
        curr = _curr()
        if rid == Gtk.ResponseType.NONE or rid == Gtk.ResponseType.DELETE_EVENT:
            self.changes = False
            dialog.hide()
            return
        couple = {'fem': (self.data['fname'], self.data['ftab'], self.data['fid']),
                  'mas': (self.data['mname'], self.data['mtab'], self.data['mid']),
                  'dates': []}
        curr.couples.append(couple)
        coupmodel = Gtk.ListStore(str, str, int, str, str, int)
        for c in curr.couples:
            coupmodel.append([c['fem'][0], c['fem'][1], c['fem'][2],
                              c['mas'][0], c['mas'][1], c['mas'][2]])
        self.coupview.set_model(coupmodel)
        self.coupview.get_selection().select_path(Gtk.TreePath.new_from_indices([len(coupmodel) - 1]))
        self.changes = True
        dialog.hide()

    def save_couples(self):
        if self.changes:
            _curr().save_couples(self.boss.app)

    def on_view_clicked(self, view, event, menu):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            x = int(event.x)
            y = int(event.y)
            pthinfo = view.get_path_at_pos(x, y)
            if pthinfo is not None:
                path_, col, cellx, celly = pthinfo
                view.grab_focus()
                view.set_cursor(path_, col, False)
                menu.popup_at_pointer(event)
            return True

    def on_sel_changed(self, sel):
        curr = _curr()
        model, it = sel.get_selected()
        if not it:
            return
        self.coup_ix = model.get_path(it)[0]
        datemodel = Gtk.ListStore(str, str)
        for d in curr.couples[self.coup_ix]['dates']:
            datemodel.append([d[0], d[1]])
        try:
            self.dateview.set_model(datemodel)
        except AttributeError:
            pass

    def on_menuitem_activate(self, menuitem):
        curr = _curr()
        model, it = self.coupview.get_selection().get_selected()
        i = model.get_path(it)[0]
        del curr.couples[i]
        model.remove(it)
        if i >= 1:
            self.coupview.get_selection().select_path(Gtk.TreePath.new_from_indices([i - 1]))
        elif len(model) == 1:
            self.coupview.get_selection().select_path(Gtk.TreePath.new_from_indices([0]))
        else:
            datemodel = Gtk.ListStore(str, str)
            self.dateview.set_model(datemodel)
        self.changes = True

    def on_menudate_activate(self, menuitem):
        curr = _curr()
        model, it = self.dateview.get_selection().get_selected()
        i = model.get_path(it)[0]
        model.remove(it)
        del curr.couples[self.coup_ix]['dates'][i]
        self.changes = True

    def on_dateview_clicked(self, view, event, menu):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            x = int(event.x)
            y = int(event.y)
            pthinfo = view.get_path_at_pos(x, y)
            if pthinfo is not None:
                path_, col, cellx, celly = pthinfo
                view.grab_focus()
                view.set_cursor(path_, col, False)
                menu.popup_at_pointer(event)
            return True

    def on_cell_edited(self, cell, path_string, newtext):
        curr = _curr()
        model = self.dateview.get_model()
        it = model.get_iter_from_string(path_string)
        idx = model.get_path(it)[0]
        date = model.get_value(it, 0)
        curr.couples[self.coup_ix]['dates'][idx] = (date, newtext)
        ntxt = curr.couples[self.coup_ix]['dates'][idx][1]
        model.set_value(it, 1, ntxt)
        self.changes = True

    def on_add_date_clicked(self, but):
        curr = _curr()
        if len(self.coupview.get_model()) < 1:
            return
        date = self.datewid.date
        dtstring = str(date.day) + "/" + str(date.month) + "/" + str(date.year)
        model = self.dateview.get_model()
        it = model.append()
        desc = _('Acontecimiento')
        model.set(it, 0, dtstring, 1, desc)
        curr.couples[self.coup_ix]['dates'].append((dtstring, desc))
        self.changes = True


class CoupleDates(DateEntry):
    def __init__(self, parent, boss):
        DateEntry.__init__(self, boss, fullpanel=False)
        self._container = parent
        self.view = None

    def calc_and_set(self, entry):
        try:
            self.date = self.get_date()
            set_background(entry, "#ffffff")
        except ValidationError:
            self.date = None
            set_background(entry, "#ff699a")
        if self.date is None:
            return
        try:
            curr = _curr()
            model, it = self.view.get_selection().get_selected()
            if it:
                date = self.date
                dtstring = str(date.day) + "/" + str(date.month) + "/" + str(date.year)
                model.set(it, 0, dtstring)
                path_ = model.get_path(it)[0]
                desc = model.get_value(it, 1)
                coup = self._container.coup_ix
                curr.couples[coup]['dates'][path_] = (dtstring, desc)
                self._container.changes = True
        except AttributeError:
            pass
