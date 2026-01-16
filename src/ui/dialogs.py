import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw
from ..config import get_available_themes
from ..models import ProjectModel
from ..utils import load_settings, save_settings

class PersonalInformationDialog(Adw.Window):
    """Dialog to edit Global Metadata"""
    def __init__(self, parent, model, on_save_callback=None):
        super().__init__(modal=True, transient_for=parent, title="Personal Information", default_width=450, default_height=500)
        self.model = model
        self.on_save_callback = on_save_callback
        
        # Load global settings
        settings = load_settings()
        
        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup(title="Artist Identity")
        page.add(group)
        
        self.name_row = Adw.EntryRow(title="Artist Name", text=settings.get("artist_name", "") or model.metadata.artist_name)
        self.role_row = Adw.EntryRow(title="Role / Title", text=settings.get("role", "") or model.metadata.role)
        self.email_row = Adw.EntryRow(title="Contact Email", text=settings.get("email", "") or model.metadata.email)
        
        group.add(self.name_row); group.add(self.role_row); group.add(self.email_row)
        
        link_group = Adw.PreferencesGroup(title="Links")
        self.social_row = Adw.EntryRow(title="Social Link", text=settings.get("social_link", "") or model.metadata.social_link)
        self.cv_row = Adw.EntryRow(title="Resume / CV URL", text=settings.get("cv_link", "") or model.metadata.cv_link)
        link_group.add(self.social_row); link_group.add(self.cv_row)
        page.add(link_group)
        
        bio_group = Adw.PreferencesGroup(title="Biography")
        bio_row = Adw.ActionRow()
        self.bio_view = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR, top_margin=10, bottom_margin=10, left_margin=10, right_margin=10)
        self.bio_view.get_buffer().set_text(settings.get("bio", "") or model.metadata.bio)
        scroll = Gtk.ScrolledWindow(min_content_height=100, child=self.bio_view)
        scroll.set_has_frame(True)
        bio_row.set_child(scroll)
        bio_group.add(bio_row)
        page.add(bio_group)
        
        # Toolbar
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header = Adw.HeaderBar(show_end_title_buttons=False)
        header.set_title_widget(Gtk.Label(label="Personal Information", css_classes=["title"]))
        
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda _: self.close())
        header.pack_start(cancel_btn)

        save_btn = Gtk.Button(label="Save", css_classes=["suggested-action"])
        save_btn.connect("clicked", self.on_save)
        header.pack_end(save_btn)
        
        box.append(header)
        box.append(page)
        self.set_content(box)

    def on_save(self, btn):
        # Update Global Settings
        settings = load_settings()
        settings["artist_name"] = self.name_row.get_text()
        settings["role"] = self.role_row.get_text()
        settings["email"] = self.email_row.get_text()
        settings["social_link"] = self.social_row.get_text()
        settings["cv_link"] = self.cv_row.get_text()
        
        buf = self.bio_view.get_buffer()
        settings["bio"] = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        
        save_settings(settings)

        # Update Model
        m = self.model.metadata
        m.artist_name = settings["artist_name"]
        m.role = settings["role"]
        m.email = settings["email"]
        m.social_link = settings["social_link"]
        m.cv_link = settings["cv_link"]
        m.bio = settings["bio"]
        
        if self.on_save_callback:
            self.on_save_callback()
        self.close()

class TitleInputDialog(Adw.Window):
    """Dialog to input Portfolio Title for new projects"""
    def __init__(self, parent, on_confirm):
        super().__init__(modal=True, transient_for=parent, title="New Project", default_width=400, default_height=200)
        self.on_confirm = on_confirm
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20, margin_top=30, margin_bottom=30, margin_start=30, margin_end=30)
        self.set_content(content)
        
        content.append(Gtk.Label(label="Enter Portfolio Title", css_classes=["title-2"]))
        
        self.entry = Gtk.Entry(placeholder_text="My Portfolio")
        self.entry.connect("activate", self.on_create)
        self.entry.connect("notify::text", self.on_text_changed)
        content.append(self.entry)
        
        btn_box = Gtk.Box(spacing=10, halign=Gtk.Align.CENTER)
        cancel = Gtk.Button(label="Cancel")
        cancel.connect("clicked", lambda x: self.close())
        self.create_btn = Gtk.Button(label="Create", css_classes=["suggested-action"])
        self.create_btn.connect("clicked", self.on_create)
        self.create_btn.set_sensitive(False)
        btn_box.append(cancel)
        btn_box.append(self.create_btn)
        content.append(btn_box)
    
    def on_text_changed(self, entry, param):
        text = entry.get_text().strip()
        self.create_btn.set_sensitive(bool(text))
        
    def on_create(self, btn):
        text = self.entry.get_text().strip()
        if not text: return
        self.close()
        self.on_confirm(text)

class ThemeSelectionDialog(Adw.Window):
    def __init__(self, parent, on_confirm_callback):
        super().__init__(modal=True, transient_for=parent, title="Export Settings", default_width=400, default_height=300)
        self.on_confirm = on_confirm_callback
        self.themes = get_available_themes()
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20, margin_top=30, margin_bottom=30, margin_start=30, margin_end=30)
        self.set_content(content)
        content.append(Gtk.Label(label="Select a Theme", css_classes=["title-2"]))
        self.dropdown = Gtk.DropDown.new_from_strings([t[0] for t in self.themes])
        content.append(self.dropdown)
        btn_box = Gtk.Box(spacing=10, halign=Gtk.Align.CENTER)
        cancel = Gtk.Button(label="Cancel"); cancel.connect("clicked", lambda x: self.close())
        export = Gtk.Button(label="Next", css_classes=["suggested-action"]); export.connect("clicked", self.on_next)
        btn_box.append(cancel); btn_box.append(export)
        content.append(btn_box)
    def on_next(self, btn):
        idx = self.dropdown.get_selected()
        if idx != Gtk.INVALID_LIST_POSITION: self.close(); self.on_confirm(self.themes[idx][1])

class ImageViewerWindow(Adw.Window):
    def __init__(self, parent, obj):
        super().__init__(transient_for=parent, title=obj.title, default_width=1000, default_height=800)
        
        # Header
        header = Adw.HeaderBar()
        
        # Content
        scrolled = Gtk.ScrolledWindow()
        
        try:
            pic = Gtk.Picture.new_for_filename(obj.source_path)
            pic.set_content_fit(Gtk.ContentFit.SCALE_DOWN)
            scrolled.set_child(pic)
        except:
            scrolled.set_child(Gtk.Label(label="Could not load image"))
            
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(header)
        box.append(scrolled)
        scrolled.set_vexpand(True)
        
        self.set_content(box)

class PaletteDialog(Adw.Window):
    def __init__(self, parent, colors):
        super().__init__(modal=True, transient_for=parent, title="Color Palette", default_width=500, default_height=300)
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header = Adw.HeaderBar()
        main_box.append(header)
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content_box.set_margin_top(20); content_box.set_margin_bottom(20)
        content_box.set_margin_start(20); content_box.set_margin_end(20)
        main_box.append(content_box)
        
        lbl = Gtk.Label(label="Extracted Colors")
        lbl.add_css_class("title-2")
        content_box.append(lbl)
        
        grid = Gtk.Box(spacing=15, halign=Gtk.Align.CENTER)
        
        for c in colors:
            item_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            
            btn = Gtk.Button()
            btn.set_size_request(60, 60)
            
            # Using CSS provider for dynamic background color
            provider = Gtk.CssProvider()
            css = f"button {{ background-color: {c}; border-radius: 8px; }}"
            provider.load_from_data(css.encode('utf-8'))
            
            context = btn.get_style_context()
            context.add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            
            btn.set_tooltip_text(f"Copy {c}")
            btn.connect("clicked", self.on_color_click, c)
            item_box.append(btn)
            
            # Label with hex code
            hex_lbl = Gtk.Label(label=c)
            hex_lbl.set_selectable(True)
            hex_lbl.add_css_class("caption")
            item_box.append(hex_lbl)
            
            grid.append(item_box)
            
        content_box.append(grid)
        self.set_content(main_box)
        
    def on_color_click(self, btn, color):
        from gi.repository import Gdk
        Gdk.Display.get_default().get_clipboard().set(color)
        # Maybe show a small toast or label change?
        btn.set_tooltip_text("Copied!")
