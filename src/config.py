import os

APP_DIR = os.path.join(os.path.expanduser("~"), ".config", "portfolio_manager")
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "portfolio_manager_thumbs")
TEMPLATE_DIR = os.path.join(APP_DIR, "templates")
RECENT_PROJECTS_FILE = os.path.join(APP_DIR, "recent_projects.json")

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(TEMPLATE_DIR, exist_ok=True)

THEME_DARK = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>{{TITLE}}</title><style>
body{font-family:system-ui,sans-serif;background:#121212;color:#e0e0e0;padding:40px}
header{text-align:center; margin-bottom:60px;}
h1{font-weight:300;letter-spacing:2px;margin:0 0 10px 0;}
.role{color:#bb86fc; text-transform:uppercase; font-size:0.9rem; letter-spacing:1px; margin-bottom:20px;}
.bio{max-width:600px; margin:0 auto; color:#aaa; line-height:1.6;}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(350px,1fr));gap:30px;max-width:1600px;margin:0 auto}
.card{background:#1e1e1e;border-radius:12px;overflow:hidden;box-shadow:0 4px 6px rgba(0,0,0,0.3);transition:transform 0.2s; display:flex; flex-direction:column;}
.card:hover{transform:translateY(-5px)}
.card img{width:100%; height: 300px; object-fit: cover; display:block; background:#000;}
.info{padding:20px; flex-grow:1; display:flex; flex-direction:column;}
.info h2{margin:0 0 5px 0;color:#fff;font-size:1.2rem}
.meta{color:#bb86fc;font-size:0.85rem;font-weight:600;text-transform:uppercase;margin-bottom:10px}
.desc{color:#aaa;line-height:1.5;margin-bottom:15px; flex-grow:1;}
.notes{background:#222;border-left:3px solid #bb86fc;padding:10px;font-style:italic;color:#888;margin-bottom:15px;font-size:0.9em}
.btn{display:inline-block;padding:8px 16px;background:#333;color:white;text-decoration:none;border-radius:4px;font-size:0.8rem;align-self:start;}
.btn:hover{background:#444}
footer{text-align:center; margin-top:80px; padding-top:40px; border-top:1px solid #333; color:#666;}
footer a { color: #bb86fc; text-decoration: none; margin: 0 10px; }
</style></head><body>
<header>
    <h1>{{NAME}}</h1>
    <div class="role">{{ROLE}}</div>
    <div class="bio">{{BIO}}</div>
</header>
<div class="grid"></div>
<footer>
    <p>Contact: {{EMAIL}}</p>
    <p>{{LINKS}}</p>
</footer>
</body></html>"""

def ensure_templates():
    if not os.path.exists(os.path.join(TEMPLATE_DIR, "Modern Dark.html")):
        with open(os.path.join(TEMPLATE_DIR, "Modern Dark.html"), "w") as f: f.write(THEME_DARK)

def get_available_themes():
    themes = []
    if os.path.exists(TEMPLATE_DIR):
        for f in os.listdir(TEMPLATE_DIR):
            if f.endswith(".html"): themes.append((os.path.splitext(f)[0], os.path.join(TEMPLATE_DIR, f)))
    return sorted(themes)
