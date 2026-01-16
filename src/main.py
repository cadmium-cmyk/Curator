import sys
import os
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, Gdk

from .ui.orientation import WelcomeWindow
from .models import ProjectModel
from .utils import add_recent_project, load_settings

class PortfolioApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.github.cadmiumcmyk.Curator", flags=Gio.ApplicationFlags.FLAGS_NONE)
        
        # Load resource if exists (Local dev support)
        res_paths = [
            os.path.join(os.path.dirname(__file__), "..", "curator.gresource"),
            os.path.join(os.path.dirname(__file__), "..", "curator", "curator.gresource"),
        ]
        for res_path in res_paths:
            if os.path.exists(res_path):
                try:
                    res = Gio.resource_load(res_path)
                    Gio.resources_register(res)
                    break
                except Exception as e:
                    print(f"Failed to load resource: {e}")

    def do_startup(self):
        Adw.Application.do_startup(self)
        
        # Load Settings (Theme)
        settings = load_settings()
        if "theme" in settings:
            variant = settings["theme"]
            sm = Adw.StyleManager.get_default()
            if variant == "light": sm.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
            elif variant == "dark": sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
            else: sm.set_color_scheme(Adw.ColorScheme.DEFAULT)
            
        # Load CSS
        css_provider = Gtk.CssProvider()
        resource_path = "/com/github/cadmiumcmyk/Curator/style.css"
        try:
             Gio.resources_get_info(resource_path, Gio.ResourceLookupFlags.NONE)
             css_provider.load_from_resource(resource_path)
        except:
             # Fallback to local file
             css_path = os.path.join(os.path.dirname(__file__), "..", "style.css")
             if os.path.exists(css_path):
                 css_provider.load_from_path(css_path)
        
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def do_activate(self):
        # Check if we already have a window
        win = self.get_active_window()
        if not win:
            self.show_welcome()
        else:
            win.present()

    def show_welcome(self):
        win = WelcomeWindow(self, self.on_project_ready)
        win.present()

    def on_project_ready(self, result):
        # Close welcome window (which is the active window)
        active = self.get_active_window()
        if active:
            active.close()
            
        from .ui.window import PortfolioWindow
        win = PortfolioWindow(application=self)
        if isinstance(result, str):
            win.load_project_file(result)
            add_recent_project(result, win.model.metadata.portfolio_title)
        else:
            # New project: copy metadata
            win.model.metadata = result.metadata
            # Verify bindings or trigger update if needed?
            # Metadata is not bound to UI widgets automatically in PortfolioWindow init except via explicit setting.
            # But the UI is empty. Metadata is only shown in Settings Dialog or Export.
            # So this is fine.
        
        win.present()
