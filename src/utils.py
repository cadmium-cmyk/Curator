import os
import hashlib
import json
import time
from PIL import Image
from .config import CACHE_DIR, RECENT_PROJECTS_FILE, APP_DIR

SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {}
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
    except:
        pass

def load_recent_projects():
    if not os.path.exists(RECENT_PROJECTS_FILE):
        return []
    try:
        with open(RECENT_PROJECTS_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_recent_projects(projects):
    try:
        with open(RECENT_PROJECTS_FILE, 'w') as f:
            json.dump(projects, f, indent=4)
    except:
        pass

def add_recent_project(path, title=None):
    projects = load_recent_projects()
    # Normalize path
    path = os.path.abspath(path)
    
    # Resolve Title
    if not title:
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                if isinstance(data, dict) and "metadata" in data:
                    title = data["metadata"].get("portfolio_title")
        except: pass
    
    if not title:
        title = os.path.basename(path)

    name = os.path.basename(path)
    
    # Remove existing entry if present
    projects = [p for p in projects if p.get('path') != path]
    
    # Add to front
    projects.insert(0, {
        'path': path,
        'name': name,
        'title': title,
        'last_opened': time.time()
    })
    
    # Keep max 10
    projects = projects[:10]
    save_recent_projects(projects)

def remove_recent_project(path):
    projects = load_recent_projects()
    path = os.path.abspath(path)
    projects = [p for p in projects if p.get('path') != path]
    save_recent_projects(projects)

def generate_thumbnail(source_path, force=False):
    try:
        path_hash = hashlib.md5(source_path.encode('utf-8')).hexdigest()
        thumb_filename = f"{path_hash}.jpg"
        thumb_path = os.path.join(CACHE_DIR, thumb_filename)
        if os.path.exists(thumb_path) and not force: return thumb_path
        with Image.open(source_path) as img:
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            img.thumbnail((600, 600)) 
            img.save(thumb_path, "JPEG", quality=85)
        return thumb_path
    except: return None

def rotate_image(path, angle):
    try:
        with Image.open(path) as img:
            # Rotate -angle because PIL rotate is CCW, we usually mean CW for positive
            # But "Rotate CW" means -90 in PIL?
            # PIL: rotate(90) is CCW. So -90 is CW.
            rotated = img.rotate(-angle, expand=True)
            rotated.save(path)
        generate_thumbnail(path, force=True)
        return True
    except Exception as e:
        print(f"Rotation failed: {e}")
        return False

def extract_palette(path, num_colors=5):
    try:
        with Image.open(path) as img:
            img = img.resize((150, 150))
            result = img.quantize(colors=num_colors)
            palette = result.getpalette()
            colors = []
            if palette:
                # palette is [r,g,b, r,g,b, ...]
                # limited to num_colors * 3
                for i in range(0, num_colors * 3, 3):
                    if i+2 < len(palette):
                        r, g, b = palette[i], palette[i+1], palette[i+2]
                        colors.append(f"#{r:02x}{g:02x}{b:02x}")
            return colors
    except Exception as e:
        print(f"Palette extraction failed: {e}")
        return []
