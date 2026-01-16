import os
import sys
import json
import threading
import subprocess
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GObject, Gdk, GLib

from ..config import ensure_templates, APP_DIR
from ..models import ProjectModel, PortfolioAsset, ProjectMetadata
from ..utils import generate_thumbnail, rotate_image, extract_palette, load_settings, save_settings
from ..export import export_portfolio_html, export_portfolio_pdf, HAS_REPORTLAB
from .dialogs import PersonalInformationDialog, ThemeSelectionDialog, ImageViewerWindow, PaletteDialog, TitleInputDialog

# Load UI content
template_args = {}
resource_path = "/com/github/cadmiumcmyk/Curator/window.ui"
try:
    Gio.resources_lookup_data(resource_path, Gio.ResourceLookupFlags.NONE)
    template_args['resource_path'] = resource_path
except:
    ui_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../window.ui"))
    if os.path.exists(ui_path):
        with open(ui_path, 'r') as f:
            template_args['string'] = f.read()

@Gtk.Template(**template_args)
class PortfolioWindow(Adw.ApplicationWindow):
    __gtype_name__ = "PortfolioWindow"
    
    toast_overlay = Gtk.Template.Child()
    split_view = Gtk.Template.Child()
    sidebar_stack = Gtk.Template.Child()
    ent_title = Gtk.Template.Child()
    ent_desc = Gtk.Template.Child()
    ent_med = Gtk.Template.Child()
    ent_year = Gtk.Template.Child()
    ent_link = Gtk.Template.Child()
    ent_new_tag = Gtk.Template.Child()
    btn_add_tag = Gtk.Template.Child()
    tag_flowbox = Gtk.Template.Child()
    n_view = Gtk.Template.Child()
    btn_delete = Gtk.Template.Child()
    btn_add = Gtk.Template.Child()
    # btn_back = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    sort_dropdown = Gtk.Template.Child()
    stack = Gtk.Template.Child()
    grid_view = Gtk.Template.Child()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model = ProjectModel()
        self.current_obj = None
        self.project_path = None
        
        # Auto-save every 5 minutes (300 seconds)
        GLib.timeout_add_seconds(300, self.auto_save)
        
        self.force_close = False
        
        # Initialize sidebar state
        self.sidebar_stack.set_visible_child_name("empty")

        # Setup GridView with Search Filter and Sorter
        self.filter = Gtk.CustomFilter.new(self.filter_func)
        self.filter_model = Gtk.FilterListModel(model=self.model.store, filter=self.filter)
        
        self.sorter = Gtk.CustomSorter.new(self.sort_func, None)
        self.sort_model = Gtk.SortListModel(model=self.filter_model, sorter=self.sorter)

        fac = Gtk.SignalListItemFactory()
        fac.connect("setup", self.setup_item)
        fac.connect("bind", self.bind_item)
        self.sel_model = Gtk.MultiSelection(model=self.sort_model)
        self.sel_model.connect("selection-changed", self.on_sel)
        self.grid_view.set_model(self.sel_model)
        self.grid_view.set_factory(fac)

        # Drop Target
        drop = Gtk.DropTarget.new(type=Gdk.FileList, actions=Gdk.DragAction.COPY)
        drop.connect("drop", self.on_drop)
        self.add_controller(drop)

        # Connect Signals
        self.btn_add.connect("clicked", self.on_add_click)
        self.btn_delete.connect("clicked", self.on_delete)
        # self.btn_back.connect("clicked", self.on_back_clicked)
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.sort_dropdown.connect("notify::selected", self.on_sort_changed)
        
        self.btn_add_tag.connect("clicked", self.on_add_tag)
        self.ent_new_tag.connect("entry-activated", self.on_add_tag)
        
        for e in [self.ent_title, self.ent_desc, self.ent_med, self.ent_year, self.ent_link]:
            e.connect("notify::text", self.on_edit)
        
        self.n_buf = self.n_view.get_buffer()
        self.n_buf.connect("changed", self.on_note_change)
        
        self.model.store.connect("items-changed", lambda s,p,r,a: self.stack.set_visible_child_name("empty" if s.get_n_items()==0 else "grid"))
        if self.model.store.get_n_items()==0: self.stack.set_visible_child_name("empty")

        # Actions
        self.install_action("new", None, self.on_new)
        self.install_action("settings", None, self.on_settings)
        self.install_action("import", None, self.on_import)
        self.install_action("save", None, self.on_save)
        self.install_action("export_html", None, self.on_export_html)
        self.install_action("export_pdf", None, self.on_export_pdf)
        self.install_action("theme", "s", self.on_theme)
        self.install_action("about", None, self.on_about)

    def install_action(self, name, param_type, callback):
        action = Gio.SimpleAction.new(name, GLib.VariantType.new(param_type) if param_type else None)
        action.connect("activate", callback)
        self.add_action(action)
    
    def do_close_request(self):
        if self.force_close:
            return False
            
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Save Changes?",
            body="Do you want to save your changes before closing?",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("discard", "Discard")
        dialog.add_response("save", "Save")
        
        dialog.set_response_appearance("discard", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        
        dialog.connect("response", self.on_close_response)
        dialog.present()
        
        return True # Block
    
    def on_close_response(self, dialog, response):
        if response == "save":
            if self.project_path:
                self.auto_save()
                self.force_close = True
                self.close()
            else:
                name = self.model.metadata.portfolio_title + ".json" if self.model.metadata.portfolio_title else "portfolio.json"
                d=Gtk.FileDialog(initial_name=name)
                d.save(self, None, self.do_save_finish_close_req)
        elif response == "discard":
            self.force_close = True
            self.close()
            
    def do_save_finish_close_req(self, d, r):
        try:
            f=d.save_finish(r)
            path = f.get_path()
            self.project_path = path
            self.auto_save()
            self.force_close = True
            self.close()
        except: pass

    def auto_save(self):
        try:
            target_path = self.project_path
            if not target_path:
                target_path = os.path.join(APP_DIR, "autosave.json")
                os.makedirs(APP_DIR, exist_ok=True)
            
            payload = {
                "metadata": self.model.metadata.to_dict(),
                "assets": [a.to_dict() for a in self.model.get_all_assets()]
            }
            with open(target_path, 'w') as o: json.dump(payload, o, indent=4)
        except Exception as e: print(f"Auto-save failed: {e}")
        return True # Keep timer running

    def filter_func(self, item, *args):
        query = self.search_entry.get_text().lower()
        if not query: return True
        return query in item.title.lower() or query in item.tags_string.lower()

    def on_search_changed(self, entry):
        self.filter.changed(Gtk.FilterChange.DIFFERENT)

    def sort_func(self, a, b, *args):
        idx = self.sort_dropdown.get_selected()
        if idx == 0: 
            return 0 # Maintain original order? No, GtkSorter needs comparison.
            # Let's use ID or title for stability if 0.
            # Better: if we want "Date Added" effectively means "Unsorted" relative to the store?
            # CustomSorter with 0 implies equality.
            pass
        elif idx == 1: # Title A-Z
            return (a.title.lower() > b.title.lower()) - (a.title.lower() < b.title.lower())
        elif idx == 2: # Year Created
            # Handle empty years
            ya = a.year or "0"
            yb = b.year or "0"
            return (ya > yb) - (ya < yb)
        return 0

    def on_sort_changed(self, *args):
        self.sorter.set_sort_func(self.sort_func, None)
        self.sorter.changed(Gtk.SorterChange.DIFFERENT)

    # --- LOGIC ---
    # def on_back_clicked(self, btn):
    #     dialog = Adw.MessageDialog(
    #         transient_for=self,
    #         heading="Save Project?",
    #         body="Do you want to save changes before closing?",
    #     )
    #     dialog.add_response("cancel", "Cancel")
    #     dialog.add_response("discard", "Discard")
    #     dialog.add_response("save", "Save")
    #     dialog.set_response_appearance("discard", Adw.ResponseAppearance.DESTRUCTIVE)
    #     dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
    #     dialog.connect("response", self.on_back_response)
    #     dialog.present()

    # def on_back_response(self, dialog, response):
    #     if response == "cancel":
    #         pass
    #     elif response == "discard":
    #         self.get_application().show_welcome()
    #         self.close()
    #     elif response == "save":
    #         self.do_save_and_close()

    def do_save_and_close(self):
        # reuse save logic but then close
        if self.project_path:
            self.auto_save()
            self.get_application().show_welcome()
            self.close()
        else:
            name = self.model.metadata.portfolio_title + ".json" if self.model.metadata.portfolio_title else "portfolio.json"
            d=Gtk.FileDialog(initial_name=name)
            d.save(self, None, self.do_save_finish_and_close)
            
    def do_save_finish_and_close(self, d, r):
        try:
            f=d.save_finish(r)
            path = f.get_path()
            self.project_path = path
            self.auto_save()
            self.get_application().show_welcome()
            self.close()
        except Exception as e: print(e)

    def on_add_click(self, b): 
        d=Gtk.FileDialog(title="Select Images", accept_label="Add")
        f=Gio.ListStore.new(Gtk.FileFilter); i=Gtk.FileFilter(); i.set_name("Images"); i.add_mime_type("image/*"); f.append(i); d.set_filters(f)
        d.open_multiple(self, None, self.do_add_finish)

    def do_add_finish(self, d, r):
        try:
            files = d.open_multiple_finish(r)
            if files:
                for f in files:
                    self.add_path(f.get_path())
        except Exception as e:
            print(f"Error adding files: {e}")
    
    def add_path(self, p):
        if p and os.path.splitext(p)[1].lower() in {".png",".jpg",".jpeg",".webp",".svg"}:
            self.model.add_asset(PortfolioAsset(title=os.path.basename(p), source_path=p, thumbnail_path=generate_thumbnail(p)))
            
    def on_drop(self, t, v, x, y): [self.add_path(f.get_path()) for f in v.get_files()]; return True
    
    def on_delete(self, b):
        # Bulk Delete
        bitset = self.sel_model.get_selection()
        # We need to collect items first because removing invalidates indices
        to_remove = []
        def collect(i, *args):
            obj = self.sel_model.get_item(i)
            if obj: to_remove.append(obj)
            return True
        bitset.foreach(collect, None)
        
        if not to_remove: return

        # Prepare Undo Data
        undo_data = []
        store = self.model.store
        for obj in to_remove:
            for i in range(store.get_n_items()):
                if store.get_item(i) == obj:
                    undo_data.append((i, obj))
                    break
        
        # Remove
        for obj in to_remove:
            self.model.remove_asset_object(obj)
            
        # Toast
        toast = Adw.Toast.new(f"Deleted {len(to_remove)} items")
        toast.set_button_label("Undo")
        toast.connect("button-clicked", lambda t: self.restore_items(undo_data))
        self.toast_overlay.add_toast(toast)

    def restore_items(self, data):
        # Sort by index ascending to restore positions
        data.sort(key=lambda x: x[0])
        for i, obj in data:
            self.model.insert_asset_object(i, obj)

    def on_add_tag(self, widget):
        text = self.ent_new_tag.get_text().strip()
        if not text: return

        bitset = self.sel_model.get_selection()
        size = bitset.get_size()
        
        if size == 1 and self.current_obj:
            tags = self.current_obj.get_asset().tags
            if text not in tags:
                tags.append(text)
                self.current_obj.notify("tags-string")
                self.update_tag_view()
        elif size > 1:
            # Bulk add
            def apply_tag(i, *args):
                obj = self.sel_model.get_item(i)
                if obj:
                    tags = obj.get_asset().tags
                    if text not in tags:
                        tags.append(text)
                        obj.notify("tags-string")
                return True
            bitset.foreach(apply_tag, None)
            self.toast_overlay.add_toast(Adw.Toast.new(f"Added tag '{text}' to selection"))
            
        self.ent_new_tag.set_text("")

    def update_tag_view(self):
        # Clear existing
        child = self.tag_flowbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.tag_flowbox.remove(child)
            child = next_child
            
        if not self.current_obj: return
        
        for tag in self.current_obj.get_asset().tags:
            self.tag_flowbox.append(self.create_tag_widget(tag))

    def create_tag_widget(self, tag):
        box = Gtk.Box(css_classes=["tag-chip"])
        lbl = Gtk.Label(label=tag)
        btn = Gtk.Button(icon_name="window-close-symbolic", css_classes=["flat"])
        btn.connect("clicked", lambda b: self.remove_tag(tag))
        box.append(lbl)
        box.append(btn)
        return box

    def remove_tag(self, tag):
        if not self.current_obj: return
        tags = self.current_obj.get_asset().tags
        if tag in tags:
            tags.remove(tag)
            self.current_obj.notify("tags-string")
            self.update_tag_view()

    def on_sel(self, m, p, n):
        # MultiSelection logic
        bitset = m.get_selection()
        size = bitset.get_size()
        
        if size == 1:
            # Single selection - show details
            idx = bitset.get_nth(0)
            s = m.get_item(idx)
            self.current_obj = s
            if s:
                self.ent_title.set_text(s.title); self.ent_desc.set_text(s.description)
                self.ent_med.set_text(s.medium); self.ent_year.set_text(s.year); self.ent_link.set_text(s.link)
                self.update_tag_view()
                self.n_buf.set_text(s.notes)
                # Enable inputs
                self.ent_title.set_sensitive(True)
                self.sidebar_stack.set_visible_child_name("details")
        elif size > 1:
            # Multi selection
            self.current_obj = None # Avoid editing random item
            self.ent_title.set_text(f"{size} Items Selected")
            self.ent_title.set_sensitive(False) # Disable title edit
            # We could allow bulk tagging here
            self.update_tag_view() # Clear it since current_obj is None
            self.sidebar_stack.set_visible_child_name("details")
        else:
            self.current_obj = None
            self.update_tag_view()
            self.sidebar_stack.set_visible_child_name("empty")

    def on_edit(self, w, p):
        # Bulk edit support for tags? For now just single
        if self.current_obj:
            if w==self.ent_title: self.current_obj.title=w.get_text()
            elif w==self.ent_desc: self.current_obj.description=w.get_text()
            elif w==self.ent_med: self.current_obj.medium=w.get_text()
            elif w==self.ent_year: self.current_obj.year=w.get_text()
            elif w==self.ent_link: self.current_obj.link=w.get_text()
    def on_note_change(self, b): 
        if self.current_obj: s,e=b.get_bounds(); self.current_obj.notes=b.get_text(s,e,True)

    # --- SETTINGS & SAVE/LOAD ---
    def on_new(self, a, p):
        # Trigger save prompt if needed, then show Title Dialog
        # For simplicity, we can use the close request logic or just ask directly
        # But close request closes the window.
        # Let's simple check: if project_path is None and items > 0, or modified?
        # We don't track modification flag perfectly yet, just auto-save.
        
        # If we just want to start new:
        TitleInputDialog(self, self.do_new_project).present()

    def do_new_project(self, title):
        # Verify if we should save current? 
        # For now, let's assume auto-save ran or user is okay. 
        # A more robust solution would check `self.model` state.
        
        # Create new model
        self.model.clear()
        self.model.metadata.portfolio_title = title
        
        # Reload personal info
        settings = load_settings()
        m = self.model.metadata
        m.artist_name = settings.get("artist_name", m.artist_name)
        m.role = settings.get("role", m.role)
        m.email = settings.get("email", m.email)
        m.social_link = settings.get("social_link", m.social_link)
        m.cv_link = settings.get("cv_link", m.cv_link)
        m.bio = settings.get("bio", m.bio)
        
        self.project_path = None
        self.toast_overlay.add_toast(Adw.Toast.new("New Project Created"))

    def on_settings(self, a, p): PersonalInformationDialog(self, self.model).present()
    
    def on_save(self, a, p): 
        name = self.model.metadata.portfolio_title + ".json" if self.model.metadata.portfolio_title else "portfolio.json"
        d=Gtk.FileDialog(initial_name=name); d.save(self, None, self.do_save)
    def do_save(self, d, r):
        try:
            f=d.save_finish(r)
            path = f.get_path()
            payload = {
                "metadata": self.model.metadata.to_dict(),
                "assets": [a.to_dict() for a in self.model.get_all_assets()]
            }
            with open(path,'w') as o: json.dump(payload, o, indent=4)
            self.project_path = path
            self.toast_overlay.add_toast(Adw.Toast.new("Saved"))
        except Exception as e: print(e)

    def on_import(self, a, p): 
        d=Gtk.FileDialog()
        filters = Gio.ListStore.new(Gtk.FileFilter)
        f = Gtk.FileFilter()
        f.set_name("Portfolio Files")
        f.add_pattern("*.json")
        filters.append(f)
        d.set_filters(filters)
        d.set_default_filter(f)
        d.open(self, None, self.do_import)
    def do_import(self, d, r):
        try:
            f=d.open_finish(r)
            self.load_project_file(f.get_path())
        except Exception as e: print(e)
    
    def load_project_file(self, path):
         with open(path,'r') as i: data=json.load(i)
         self.model.clear()
         if isinstance(data, list):
             for x in data: self.model.add_asset(PortfolioAsset.from_dict(x))
         else:
             if "metadata" in data: self.model.metadata = ProjectMetadata.from_dict(data["metadata"])
             if "assets" in data: 
                 for x in data["assets"]: self.model.add_asset(PortfolioAsset.from_dict(x))
         self.project_path = path
         self.toast_overlay.add_toast(Adw.Toast.new("Loaded"))

    # --- EXPORT ---
    def on_export_html(self, a, p): ensure_templates(); ThemeSelectionDialog(self, lambda path: self.do_export_html(path)).present()
    def do_export_html(self, t_path): self.pend_t=t_path; d=Gtk.FileDialog(); d.select_folder(self, None, self.fin_export_html)
    def fin_export_html(self, d, r):
        try: 
            f=d.select_folder_finish(r)
            # Run in thread
            assets = self.model.get_all_assets()
            meta = self.model.metadata
            threading.Thread(target=self.run_export_html, args=(assets, meta, f.get_path(), self.pend_t)).start()
        except: pass
    
    def run_export_html(self, assets, meta, out_dir, t_path):
        GLib.idle_add(lambda: self.toast_overlay.add_toast(Adw.Toast.new("Exporting Website...")))
        export_portfolio_html(assets, meta, out_dir, t_path)
        GLib.idle_add(lambda: self.toast_overlay.add_toast(Adw.Toast.new("Website Export Complete")))

    def on_export_pdf(self, a, p): 
        if not HAS_REPORTLAB: self.toast_overlay.add_toast(Adw.Toast.new("Install reportlab first")); return
        d=Gtk.FileDialog(initial_name="Portfolio.pdf"); d.save(self, None, self.fin_export_pdf)
    def fin_export_pdf(self, d, r):
        try: 
            f=d.save_finish(r)
            assets = self.model.get_all_assets()
            meta = self.model.metadata
            threading.Thread(target=self.run_export_pdf, args=(assets, meta, f.get_path())).start()
        except: pass

    def run_export_pdf(self, assets, meta, path):
        GLib.idle_add(lambda: self.toast_overlay.add_toast(Adw.Toast.new("Exporting PDF...")))
        export_portfolio_pdf(assets, meta, path)
        GLib.idle_add(lambda: self.toast_overlay.add_toast(Adw.Toast.new("PDF Export Complete")))

    # --- THEME & ABOUT ---
    def on_theme(self, a, p):
        variant = p.get_string()
        sm = Adw.StyleManager.get_default()
        if variant == "light": sm.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        elif variant == "dark": sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else: sm.set_color_scheme(Adw.ColorScheme.DEFAULT)
        
        # Save persistence
        settings = load_settings()
        settings["theme"] = variant
        save_settings(settings)
    
    def on_about(self, a, p):
        win = Adw.AboutWindow(
            application_name="Curator",
            application_icon="com.github.cadmiumcmyk.Curator",
            developer_name="Andrew Blair",
            version="1.0",
            copyright="© 2026 Andrew Blair",
            website="https://github.com/cadmiumcmyk/Curator",
            issue_url="https://github.com/cadmiumcmyk/Curator/issues",
            license_type=Gtk.License.GPL_3_0,
            modal=True,
            transient_for=self
        )
        win.present()

    # --- FACTORY ---
    def setup_item(self, f, i):
        fr=Gtk.Frame(css_classes=["card"]); ov=Gtk.Overlay(); fr.set_child(ov)
        pic=Gtk.Picture(content_fit=Gtk.ContentFit.COVER); pic.set_size_request(-1,240); ov.set_child(pic)
        bx=Gtk.Box(valign=Gtk.Align.END, css_classes=["osd"]); bx.set_size_request(-1,40)
        lbl=Gtk.Label(ellipsize=3, hexpand=True, margin_start=8, margin_end=8); bx.append(lbl); ov.add_overlay(bx)
        dr=Gtk.DragSource(actions=Gdk.DragAction.MOVE); dr.connect("prepare", lambda s,x,y,i: Gdk.ContentProvider.new_for_value(i.get_position()), i); fr.add_controller(dr)
        dt=Gtk.DropTarget.new(GObject.TYPE_INT, Gdk.DragAction.MOVE); dt.connect("drop", lambda t,v,x,y,i: self.model.reorder_asset(v, i.get_position()+(1 if x>t.get_widget().get_width()/2 else 0)) or True, i); fr.add_controller(dt)
        
        # Context Menu
        gc = Gtk.GestureClick(button=3)
        gc.connect("pressed", self.on_context_menu, i)
        fr.add_controller(gc)
        
        # Double Click
        dc = Gtk.GestureClick(button=1)
        dc.connect("pressed", self.on_item_double_click, i)
        fr.add_controller(dc)
        
        i.set_child(fr)

    def on_item_double_click(self, gesture, n_press, x, y, list_item):
        if n_press == 2:
            obj = list_item.get_item()
            if obj and obj.source_path:
                ImageViewerWindow(self, obj).present()

    def on_context_menu(self, gesture, n_press, x, y, list_item):
        obj = list_item.get_item()
        if not obj: return
        
        pop = Gtk.Popover()
        pop.set_parent(gesture.get_widget())
        pop.connect("closed", lambda p: p.unparent())
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        box.set_margin_top(5); box.set_margin_bottom(5)
        box.set_margin_start(5); box.set_margin_end(5)
        
        def btn(label, cb):
            b = Gtk.Button(label=label)
            b.add_css_class("flat")
            b.set_halign(Gtk.Align.START)
            b.connect("clicked", lambda _: [cb(obj), pop.popdown()])
            box.append(b)

        btn("Reveal in File Manager", self.on_reveal_asset)
        btn("Copy Image Path", self.on_copy_path)
        btn("Open in Default Viewer", self.on_open_asset)
        
        box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        
        btn("Rotate CW (90°)", lambda o: self.on_rotate(o, 90))
        btn("Rotate CCW (90°)", lambda o: self.on_rotate(o, -90))
        btn("Extract Palette", self.on_extract_palette)
        
        box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        
        btn("Delete", self.on_delete_asset)
        
        pop.set_child(box)
        pop.set_has_arrow(False)
        rect = Gdk.Rectangle()
        rect.x = int(x); rect.y = int(y); rect.width=1; rect.height=1
        pop.set_pointing_to(rect)
        pop.popup()

    def on_reveal_asset(self, obj):
        path = obj.source_path
        if not path or not os.path.exists(path): return
        try:
            if sys.platform == "win32": subprocess.Popen(["explorer", "/select,", path])
            elif sys.platform == "darwin": subprocess.Popen(["open", "-R", path])
            else: subprocess.Popen(["xdg-open", os.path.dirname(path)])
        except: pass

    def on_copy_path(self, obj):
        if obj.source_path:
            Gdk.Display.get_default().get_clipboard().set(obj.source_path)
            self.toast_overlay.add_toast(Adw.Toast.new("Path copied to clipboard"))

    def on_open_asset(self, obj):
        if obj.source_path and os.path.exists(obj.source_path):
            try:
                if sys.platform == "win32": os.startfile(obj.source_path)
                elif sys.platform == "darwin": subprocess.Popen(["open", obj.source_path])
                else: subprocess.Popen(["xdg-open", obj.source_path])
            except: pass

    def on_delete_asset(self, obj):
        # Find index for undo
        idx = -1
        store = self.model.store
        for i in range(store.get_n_items()):
            if store.get_item(i) == obj:
                idx = i
                break
        
        self.model.remove_asset_object(obj)
        
        if idx != -1:
            toast = Adw.Toast.new("Item deleted")
            toast.set_button_label("Undo")
            toast.connect("button-clicked", lambda t: self.model.insert_asset_object(idx, obj))
            self.toast_overlay.add_toast(toast)

    def on_rotate(self, obj, angle):
        if obj.source_path and os.path.exists(obj.source_path):
            if rotate_image(obj.source_path, angle):
                obj.notify("thumbnail-path")
                # Also force grid update
                self.toast_overlay.add_toast(Adw.Toast.new("Image Rotated"))

    def on_extract_palette(self, obj):
        if obj.source_path and os.path.exists(obj.source_path):
            colors = extract_palette(obj.source_path)
            if colors:
                PaletteDialog(self, colors).present()
            else:
                self.toast_overlay.add_toast(Adw.Toast.new("Could not extract palette"))

    def bind_item(self, f, i):
        fr=i.get_child(); ov=fr.get_child(); pic=ov.get_child(); lbl=pic.get_next_sibling().get_first_child(); obj=i.get_item()
        obj.bind_property("title", lbl, "label", GObject.BindingFlags.SYNC_CREATE)
        if obj.thumbnail_path and os.path.exists(obj.thumbnail_path): pic.set_filename(obj.thumbnail_path)
