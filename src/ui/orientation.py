import os
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Pango, GLib, Gio

import json
from .dialogs import TitleInputDialog, PersonalInformationDialog
from ..models import ProjectModel
from ..utils import load_recent_projects, remove_recent_project, load_settings, save_recent_projects

class WelcomeWindow(Adw.Window):
    def __init__(self, app, on_project_ready):
        super().__init__(application=app, title="", default_width=900, default_height=600)
        self.on_project_ready = on_project_ready
        
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)
        
        # Header Bar
        header = Adw.HeaderBar()
        header.add_css_class("flat")
        main_box.append(header)
        
        # Content Split
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        content_box.set_vexpand(True)
        main_box.append(content_box)
        
        
        # --- LEFT PANEL: RECENT PROJECTS ---
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        left_box.set_size_request(350, -1)
        left_box.set_margin_top(20)
        left_box.set_margin_bottom(20)
        left_box.set_margin_start(20)
        left_box.set_margin_end(20)
        left_box.add_css_class("flat")
        
        
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        self.recent_list = Gtk.ListBox()
        self.recent_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.recent_list.connect("row-activated", self.on_recent_row_activated)
        self.recent_list.add_css_class("boxed-list")
        
        scrolled.set_child(self.recent_list)
        left_box.append(scrolled)
        
        content_box.append(left_box)
        
        # Separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        #content_box.append(sep)
        
        # --- RIGHT PANEL: QUICK ACTIONS ---
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        right_box.set_hexpand(True)
        right_box.set_valign(Gtk.Align.CENTER)
        right_box.set_halign(Gtk.Align.CENTER)
        
        image = Gtk.Image.new_from_icon_name("applications-graphics-symbolic")

        # Force the icon to be 64x64 pixels
        image.set_pixel_size(128)
        image.get_style_context().add_class("dim-label")
        right_box.append(image)
        
        
        sub = Gtk.Label(label="Portfolio Manager", css_classes=["title-2"])
        sub.get_style_context().add_class("dim-label")
        right_box.append(sub)
        
        # Actions Box
        actions_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        actions_box.set_margin_top(40)
        
        # Profile
        btn_prof = Gtk.Button(label="Personal Information")
        btn_prof.add_css_class("pill")
        btn_prof.set_size_request(250, 50)
        btn_prof.connect("clicked", self.on_profile)
        
        box_prof = Gtk.Box(spacing=10)
        box_prof.set_halign(Gtk.Align.CENTER)
        box_prof.append(Gtk.Image.new_from_icon_name("avatar-default-symbolic"))
        box_prof.append(Gtk.Label(label="Profile"))
        btn_prof.set_child(box_prof)
        
        actions_box.append(btn_prof)
        
        # New Project
        btn_new = Gtk.Button(label="Create New Project")
        btn_new.add_css_class("pill")
        btn_new.add_css_class("suggested-action")
        btn_new.set_size_request(250, 50)
        btn_new.connect("clicked", self.on_new)
        
        # Icon for new project
        box_new = Gtk.Box(spacing=10)
        box_new.set_halign(Gtk.Align.CENTER)
        box_new.append(Gtk.Image.new_from_icon_name("document-new-symbolic"))
        box_new.append(Gtk.Label(label="Create New Project"))
        btn_new.set_child(box_new)
        
        actions_box.append(btn_new)
        
        # Open Project
        btn_open = Gtk.Button(label="Open Existing Project...")
        btn_open.add_css_class("pill")
        btn_open.set_size_request(250, 50)
        btn_open.connect("clicked", self.on_load)
        
        box_open = Gtk.Box(spacing=10)
        box_open.set_halign(Gtk.Align.CENTER)
        box_open.append(Gtk.Image.new_from_icon_name("document-open-symbolic"))
        box_open.append(Gtk.Label(label="Open Existing..."))
        btn_open.set_child(box_open)
        
        actions_box.append(btn_open)
        
        right_box.append(actions_box)
        content_box.append(right_box)
        
        self.populate_recent()

    def populate_recent(self):
        # Clear existing
        child = self.recent_list.get_first_child()
        while child:
            self.recent_list.remove(child)
            child = self.recent_list.get_first_child()
            
        projects = load_recent_projects()
        if not projects:
            placeholder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            placeholder.set_margin_top(50)
            placeholder.append(Gtk.Image.new_from_icon_name("folder-open-symbolic"))
            lbl = Gtk.Label(label="No recent projects")
            lbl.add_css_class("dim-label")
            placeholder.append(lbl)
            # We can't append Box directly to ListBox easily without a Row, but better to just show a placeholder row or label
            row = Gtk.ListBoxRow()
            row.set_activatable(False)
            row.set_selectable(False)
            row.set_child(placeholder)
            self.recent_list.append(row)
            return

        changed = False
        for p in projects:
            # Migration: Ensure title exists
            if 'title' not in p or not p['title']:
                try:
                    with open(p['path'], 'r') as f:
                        data = json.load(f)
                        if isinstance(data, dict) and "metadata" in data:
                            p['title'] = data["metadata"].get("portfolio_title")
                            changed = True
                except: pass
                
                if 'title' not in p or not p['title']:
                    p['title'] = p['name'] # Fallback
            
            row = Gtk.ListBoxRow()
            
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            box.set_margin_top(10)
            box.set_margin_bottom(10)
            box.set_margin_start(10)
            box.set_margin_end(10)
            
            name_lbl = Gtk.Label(label=p.get('title', p['name']), xalign=0)
            name_lbl.add_css_class("heading")
            
            path_lbl = Gtk.Label(label=p['path'], xalign=0)
            path_lbl.add_css_class("caption")
            path_lbl.add_css_class("dim-label")
            path_lbl.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
            
            box.append(name_lbl)
            box.append(path_lbl)
            
            row.set_child(box)
            # Store path in the row for retrieval
            row._project_path = p['path']
            
            self.recent_list.append(row)
            
        if changed:
            save_recent_projects(projects)

    def on_recent_row_activated(self, listbox, row):
        if not hasattr(row, '_project_path'):
            return
        
        path = row._project_path
        if not os.path.exists(path):
            self.show_missing_file_dialog(path)
        else:
            self.on_project_ready(path)

    def show_missing_file_dialog(self, path):
        # Create a custom message dialog since Adw.MessageDialog usage might vary
        # Using Adw.MessageDialog if possible
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Project Not Found",
            body=f"The file '{path}' could not be found. It may have been moved or deleted.",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("remove", "Remove from History")
        
        dialog.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        
        dialog.connect("response", self.on_missing_response, path)
        dialog.present()

    def on_missing_response(self, dialog, response, path):
        if response == "remove":
            remove_recent_project(path)
            self.populate_recent()
        dialog.close()

    def on_profile(self, btn):
        # We need a dummy model to reuse the dialog logic
        dummy_model = ProjectModel()
        PersonalInformationDialog(self, dummy_model).present()

    def on_new(self, btn):
        TitleInputDialog(self, self.on_new_project_created).present()
        
    def on_new_project_created(self, title):
        model = ProjectModel()
        model.metadata.portfolio_title = title
        
        # Initialize with personal info from settings
        settings = load_settings()
        m = model.metadata
        m.artist_name = settings.get("artist_name", m.artist_name)
        m.role = settings.get("role", m.role)
        m.email = settings.get("email", m.email)
        m.social_link = settings.get("social_link", m.social_link)
        m.cv_link = settings.get("cv_link", m.cv_link)
        m.bio = settings.get("bio", m.bio)
        
        self.on_project_ready(model)

    def on_load(self, btn):
         d = Gtk.FileDialog()
         filters = Gio.ListStore.new(Gtk.FileFilter)
         f = Gtk.FileFilter()
         f.set_name("Portfolio Files")
         f.add_pattern("*.json")
         filters.append(f)
         d.set_filters(filters)
         d.set_default_filter(f)
         d.open(self, None, self.do_load)
    
    def do_load(self, d, r):
        try:
            f = d.open_finish(r)
            self.on_project_ready(f.get_path())
        except: pass
