import os
from PIL import Image
from .config import THEME_DARK
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

def export_portfolio_html(assets, meta, output_dir, template_path):
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    html_items = []
    
    for asset in assets:
        if not os.path.exists(asset.source_path): continue
        safe_name = f"{asset.id}.jpg"
        dest_path = os.path.join(images_dir, safe_name)
        
        # Optimization: Skip if destination exists and is newer than source
        should_process = True
        if os.path.exists(dest_path):
            try:
                if os.path.getmtime(asset.source_path) <= os.path.getmtime(dest_path):
                    should_process = False
            except:
                pass # If error checking times, re-process to be safe
        
        if should_process:
            try:
                with Image.open(asset.source_path) as img:
                    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                    img.thumbnail((1920, 1920)); img.save(dest_path, "JPEG", quality=85)
            except: continue
        
        m_txt = f'<p class="meta">{asset.medium} {f"| {asset.year}" if asset.year else ""}</p>' if (asset.year or asset.medium) else ""
        link = f'<a href="{asset.link}" class="btn" target="_blank">View Project</a>' if asset.link else ""
        notes = f'<div class="notes">{asset.notes}</div>' if asset.notes else ""
        html_items.append(f"""<div class="card"><img src="images/{safe_name}" loading="lazy"><div class="info"><h2>{asset.title}</h2>{m_txt}<p class="desc">{asset.description}</p>{notes}{link}</div></div>""")

    try:
        with open(template_path, "r") as f: content = f.read()
    except: content = THEME_DARK
    
    # Inject Metadata
    content = content.replace("{{TITLE}}", meta.portfolio_title)
    content = content.replace("{{NAME}}", meta.artist_name)
    content = content.replace("{{ROLE}}", meta.role)
    content = content.replace("{{BIO}}", meta.bio)
    content = content.replace("{{EMAIL}}", meta.email)
    
    links = []
    if meta.social_link: links.append(f'<a href="{meta.social_link}">Social</a>')
    if meta.cv_link: links.append(f'<a href="{meta.cv_link}">Resume/CV</a>')
    content = content.replace("{{LINKS}}", " | ".join(links))
    
    content = content.replace("", "".join(html_items))
    with open(os.path.join(output_dir, "index.html"), "w") as f: f.write(content)

def export_portfolio_pdf(assets, meta, output_filename):
    if not HAS_REPORTLAB: return False
    
    c = canvas.Canvas(output_filename, pagesize=A4)
    width, height = A4
    
    # --- Title Page ---
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(width/2, height/2 + 60, meta.artist_name.upper())
    c.setFont("Helvetica", 14)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawCentredString(width/2, height/2 + 30, meta.role)
    
    c.setFont("Helvetica", 12)
    c.setFillColorRGB(0,0,0)
    c.drawCentredString(width/2, height/2 - 20, meta.email)
    if meta.social_link: c.drawCentredString(width/2, height/2 - 40, meta.social_link)
    
    # Draw Bio
    text_obj = c.beginText(100, height/2 - 100)
    text_obj.setFont("Helvetica", 11)
    text_obj.setTextOrigin(100, height/2 - 100)
    # Simple wrap
    for line in meta.bio.split('\n'):
        text_obj.textLine(line)
    c.drawText(text_obj)
    
    c.showPage()
    
    # --- Assets ---
    for asset in assets:
        if not os.path.exists(asset.source_path): continue
        try:
            img = ImageReader(asset.source_path)
            iw, ih = img.getSize(); aspect = ih / float(iw)
            print_w = width - 100; print_h = height * 0.55
            draw_w = print_w; draw_h = print_w * aspect
            if draw_h > print_h: draw_h = print_h; draw_w = draw_h / aspect
            
            x_pos = (width - draw_w) / 2
            y_pos = height - 60 - draw_h
            
            c.drawImage(img, x_pos, y_pos, width=draw_w, height=draw_h, preserveAspectRatio=True)
            
            text_y = y_pos - 40
            c.setFont("Helvetica-Bold", 18); c.drawString(50, text_y, asset.title); text_y -= 25
            
            meta_txt = f"{asset.medium}"
            if asset.year: meta_txt += f" | {asset.year}"
            c.setFont("Helvetica-Oblique", 12); c.setFillColorRGB(0.4, 0.4, 0.4)
            c.drawString(50, text_y, meta_txt); text_y -= 30
            
            c.setFont("Helvetica", 12); c.setFillColorRGB(0, 0, 0)
            c.drawString(50, text_y, asset.description[:100] + "..." if len(asset.description)>100 else asset.description)
            c.showPage()
        except: pass
    c.save()
