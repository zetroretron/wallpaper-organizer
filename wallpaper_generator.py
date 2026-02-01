"""
Wallpaper Generator - Smart Blending Edition
Widgets blend naturally with the wallpaper using glassmorphism and adaptive colors.
"""
from datetime import datetime, timedelta
import calendar
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import numpy as np

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

from config import (
    THEMES, CATEGORY_COLORS, CALENDAR_STYLES, WALLPAPER_CONFIG, OUTPUT_DIR,
    load_settings, load_notes, get_theme
)


# ============================================================================
# SMART BLENDING: Glassmorphism
# ============================================================================

def apply_glassmorphism(base_image: Image.Image, region: tuple,
                        blur_radius: int = 25,
                        tint_color: tuple = (255, 255, 255),
                        tint_opacity: float = 0.15,
                        brightness: float = 1.0,
                        border_radius: int = 20) -> Image.Image:
    """
    Apply frosted glass effect to a region of the image.
    The widget background becomes a blurred version of what's behind it.
    """
    x1, y1, x2, y2 = region
    w, h = x2 - x1, y2 - y1
    
    # Crop the region
    cropped = base_image.crop(region).convert('RGBA')
    
    # Apply strong blur
    blurred = cropped.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    
    # Adjust brightness
    if brightness != 1.0:
        enhancer = ImageEnhance.Brightness(blurred)
        blurred = enhancer.enhance(brightness)
    
    # Create tint overlay
    tint_layer = Image.new('RGBA', (w, h), (*tint_color, int(255 * tint_opacity)))
    
    # Create rounded mask
    mask = Image.new('L', (w, h), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([0, 0, w, h], radius=border_radius, fill=255)
    
    # Composite: blur + tint
    glass = Image.alpha_composite(blurred, tint_layer)
    
    # Apply rounded corners
    glass.putalpha(mask)
    
    return glass


def get_glass_params_for_region(image: Image.Image, region: tuple) -> dict:
    """
    Analyze region brightness and return optimal glass parameters.
    Dark areas get lighter glass, light areas get darker glass.
    """
    x1, y1, x2, y2 = region
    cropped = image.crop(region).convert('L')
    brightness = np.mean(np.array(cropped)) / 255.0
    
    if brightness < 0.3:  # Dark region
        return {
            'tint_color': (200, 200, 210),
            'tint_opacity': 0.12,
            'brightness': 1.4,
            'blur_radius': 30,
            'text_color': (255, 255, 255),
            'text_shadow': (0, 0, 0)
        }
    elif brightness > 0.7:  # Light region
        return {
            'tint_color': (20, 20, 30),
            'tint_opacity': 0.2,
            'brightness': 0.7,
            'blur_radius': 25,
            'text_color': (255, 255, 255),
            'text_shadow': (0, 0, 0)
        }
    else:  # Mid-tone
        return {
            'tint_color': (255, 255, 255),
            'tint_opacity': 0.18,
            'brightness': 1.1,
            'blur_radius': 28,
            'text_color': (255, 255, 255),
            'text_shadow': (30, 30, 40)
        }


# ============================================================================
# SMART BLENDING: Adaptive Color Extraction
# ============================================================================

def extract_dominant_colors(image: Image.Image, n_colors: int = 5) -> List[tuple]:
    """Extract dominant colors using quantization (no sklearn needed)."""
    # Resize for speed
    img_small = image.resize((80, 80)).convert('RGB')
    
    # Use PIL's quantization
    quantized = img_small.quantize(colors=n_colors, method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette()[:n_colors * 3]
    
    colors = []
    for i in range(0, len(palette), 3):
        colors.append((palette[i], palette[i+1], palette[i+2]))
    
    return colors


def calculate_luminance(color: tuple) -> float:
    """Calculate perceived luminance (0-1)."""
    r, g, b = color[:3]
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0


def get_contrast_color(bg_color: tuple) -> tuple:
    """Return white or dark gray based on background luminance."""
    lum = calculate_luminance(bg_color)
    return (255, 255, 255) if lum < 0.55 else (40, 40, 45)


def generate_accent_color(base_color: tuple, shift: float = 0.4) -> tuple:
    """Generate a vibrant accent color from base color."""
    import colorsys
    r, g, b = [x / 255.0 for x in base_color[:3]]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    
    # Shift hue and increase saturation
    h = (h + shift) % 1.0
    s = min(1.0, s * 1.5 + 0.3)
    l = max(0.4, min(0.65, l))
    
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return (int(r * 255), int(g * 255), int(b * 255))


def get_adaptive_colors(image: Image.Image, region: tuple) -> dict:
    """
    Analyze wallpaper region and return optimal colors for text/accents.
    """
    cropped = image.crop(region)
    palette = extract_dominant_colors(cropped, n_colors=4)
    
    if not palette:
        return {
            'text': (255, 255, 255),
            'text_secondary': (180, 180, 190),
            'accent': (100, 180, 255),
            'today': (255, 120, 100)
        }
    
    dominant = palette[0]
    secondary = palette[1] if len(palette) > 1 else dominant
    
    # Calculate luminance of region
    cropped_l = cropped.convert('L')
    avg_brightness = np.mean(np.array(cropped_l)) / 255.0
    
    # Text colors based on brightness
    if avg_brightness < 0.45:
        text = (255, 255, 255)
        text_secondary = (200, 200, 210)
    else:
        text = (30, 30, 35)
        text_secondary = (80, 80, 90)
    
    # Accent colors - vibrant and complementary
    accent = generate_accent_color(secondary, shift=0.5)
    today = generate_accent_color(dominant, shift=0.33)
    
    return {
        'text': text,
        'text_secondary': text_secondary,
        'accent': accent,
        'today': today,
        'dominant': dominant,
        'brightness': avg_brightness
    }


# ============================================================================
# SMART BLENDING: Region Analysis (Noise Detection)
# ============================================================================

def analyze_region_noise(image: Image.Image, region: tuple) -> dict:
    """
    Check if a region is too "noisy" for readable text.
    Returns score 0-100 and recommendation.
    """
    cropped = image.crop(region).convert('L')
    
    # Edge detection
    edges = cropped.filter(ImageFilter.FIND_EDGES)
    edge_density = np.mean(np.array(edges)) / 255.0
    
    # Variance (texture complexity)
    variance = np.var(np.array(cropped)) / (255 ** 2)
    
    # Combined score
    score = int(min(100, edge_density * 50 + variance * 150))
    
    if score < 30:
        recommendation = "excellent"
    elif score < 50:
        recommendation = "good"
    elif score < 70:
        recommendation = "warning"
    else:
        recommendation = "bad"
    
    return {'score': score, 'recommendation': recommendation}


# ============================================================================
# FONT UTILITIES
# ============================================================================

def get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """Get system font with fallback."""
    fonts = ["Segoe UI Bold", "Segoe UI", "Arial Bold", "Arial", "Calibri"]
    if not bold:
        fonts = ["Segoe UI", "Segoe UI Light", "Arial", "Calibri"]
    
    for name in fonts:
        try:
            return ImageFont.truetype(name, size)
        except:
            continue
    return ImageFont.load_default()


def draw_text_shadow(draw, pos, text, font, fill, shadow_color=(0,0,0,100), offset=2):
    """Draw text with shadow for readability."""
    x, y = pos
    # Shadow
    for dx, dy in [(-offset, 0), (offset, 0), (0, -offset), (0, offset),
                   (-offset, -offset), (offset, offset)]:
        draw.text((x + dx, y + dy), text, font=font, fill=shadow_color)
    # Main text
    draw.text(pos, text, font=font, fill=fill)


# ============================================================================
# WIDGET RENDERERS WITH SMART BLENDING
# ============================================================================

def render_calendar_widget(base_image: Image.Image, tasks: List[Dict], 
                           x: int, y: int, width: int, height: int,
                           settings: dict) -> Tuple[Image.Image, tuple]:
    """
    Render calendar widget with glassmorphism background.
    Returns (widget_image, position).
    """
    region = (x, y, x + width, y + height)
    
    # Get adaptive parameters
    glass_params = get_glass_params_for_region(base_image, region)
    colors = get_adaptive_colors(base_image, region)
    
    # Create glass background
    glass_bg = apply_glassmorphism(
        base_image, region,
        blur_radius=glass_params['blur_radius'],
        tint_color=glass_params['tint_color'],
        tint_opacity=glass_params['tint_opacity'],
        brightness=glass_params['brightness'],
        border_radius=18
    )
    
    # Draw on glass
    draw = ImageDraw.Draw(glass_bg)
    
    # Colors
    text_color = (*colors['text'], 255)
    text_secondary = (*colors['text_secondary'], 255)
    accent_color = (*colors['accent'], 255)
    today_color = (*colors['today'], 255)
    
    # Sizing
    base = max(width // 15, 13)
    padding = 20
    
    today = datetime.now()
    month_name = calendar.month_name[today.month]
    
    # Style check
    style = CALENDAR_STYLES.get(settings.get('calendar_style', 'aesthetic'), 
                                 CALENDAR_STYLES['aesthetic'])
    
    y_pos = padding + 5
    
    # Large date display (aesthetic style)
    if style.get('show_large_date', True):
        large_font = get_font(int(base * 3.5), bold=True)
        day_str = f"{today.day:02d}"
        draw_text_shadow(draw, (padding + 10, y_pos), day_str, large_font, text_color)
        
        # Month/year
        month_font = get_font(int(base * 1.1), bold=False)
        draw.text((padding + 10 + base * 4.5, y_pos + 8), month_name, 
                  font=month_font, fill=text_secondary)
        draw.text((padding + 10 + base * 4.5, y_pos + base * 1.5), str(today.year),
                  font=get_font(int(base * 0.9), bold=False), fill=text_secondary)
        
        y_pos += int(base * 4)
    else:
        # Simple header
        header_font = get_font(int(base * 1.3), bold=True)
        draw.text((width // 2, y_pos), f"{month_name} {today.year}",
                  font=header_font, fill=text_color, anchor="mt")
        y_pos += int(base * 2)
    
    # Divider
    draw.line([(padding, y_pos), (width - padding, y_pos)], 
              fill=(*text_secondary[:3], 80), width=1)
    y_pos += 12
    
    # Weekday headers
    weekdays = ["S", "M", "T", "W", "T", "F", "S"]
    cell_w = (width - padding * 2) // 7
    weekday_font = get_font(int(base * 0.8), bold=True)
    
    for i, wd in enumerate(weekdays):
        wx = padding + i * cell_w + cell_w // 2
        color = accent_color if i == 0 else text_secondary
        draw.text((wx, y_pos), wd, font=weekday_font, fill=color, anchor="mt")
    
    y_pos += int(base * 1.6)
    
    # Calendar grid
    cal = calendar.Calendar(firstweekday=6)
    month_days = cal.monthdayscalendar(today.year, today.month)
    
    # Tasks lookup
    tasks_by_date = {}
    for task in tasks:
        d = task.get("date", "")
        if d not in tasks_by_date:
            tasks_by_date[d] = []
        tasks_by_date[d].append(task)
    
    cell_h = int(base * 1.7)
    day_font = get_font(int(base * 0.9), bold=False)
    
    for week in month_days[:6]:
        for day_idx, day in enumerate(week):
            if day == 0:
                continue
            
            cx = padding + day_idx * cell_w + cell_w // 2
            date_str = f"{today.year}-{today.month:02d}-{day:02d}"
            day_tasks = tasks_by_date.get(date_str, [])
            
            # Today highlight
            if day == today.day:
                r = int(base * 0.85)
                draw.ellipse([cx - r, y_pos - r + 4, cx + r, y_pos + r + 4], fill=today_color)
                day_text_color = (255, 255, 255, 255)
            elif day_idx == 0:
                day_text_color = accent_color
            else:
                day_text_color = text_color
            
            draw.text((cx, y_pos + 4), str(day), font=day_font, fill=day_text_color, anchor="mt")
            
            # Task dots
            if day_tasks and day != today.day:
                dot_y = y_pos + int(base * 1.1)
                for j, task in enumerate(day_tasks[:2]):
                    cat = task.get("category", "default")
                    dot_color = (*CATEGORY_COLORS.get(cat, (150, 150, 150)), 255)
                    dot_x = cx - 3 + j * 7
                    draw.ellipse([dot_x - 2, dot_y, dot_x + 2, dot_y + 4], fill=dot_color)
        
        y_pos += cell_h
    
    return glass_bg, (x, y)


def render_todo_widget(base_image: Image.Image, tasks: List[Dict],
                       x: int, y: int, width: int, height: int,
                       settings: dict) -> Tuple[Image.Image, tuple]:
    """Render To-Do widget with glass effect."""
    region = (x, y, x + width, y + height)
    
    glass_params = get_glass_params_for_region(base_image, region)
    colors = get_adaptive_colors(base_image, region)
    
    glass_bg = apply_glassmorphism(
        base_image, region,
        blur_radius=glass_params['blur_radius'],
        tint_color=glass_params['tint_color'],
        tint_opacity=glass_params['tint_opacity'],
        brightness=glass_params['brightness'],
        border_radius=15
    )
    
    draw = ImageDraw.Draw(glass_bg)
    
    text_color = (*colors['text'], 255)
    text_secondary = (*colors['text_secondary'], 255)
    
    base = max(width // 14, 11)
    padding = 15
    yp = padding + 5
    
    # Header
    header_font = get_font(int(base * 1.1), bold=True)
    draw_text_shadow(draw, (padding + 5, yp), "To Do", header_font, text_color)
    yp += int(base * 2)
    
    # Divider
    draw.line([(padding, yp), (width - padding, yp)], fill=(*text_secondary[:3], 60), width=1)
    yp += 10
    
    # Tasks
    today = datetime.now().date()
    upcoming = []
    for task in tasks:
        try:
            task_date = datetime.strptime(task["date"], "%Y-%m-%d").date()
            delta = (task_date - today).days
            if -1 <= delta <= 7:
                upcoming.append((delta, task))
        except:
            continue
    
    upcoming.sort(key=lambda x: x[0])
    
    task_font = get_font(int(base * 0.85), bold=False)
    line_h = int(base * 1.5)
    max_tasks = (height - yp - padding) // line_h
    
    for delta, task in upcoming[:max_tasks]:
        if yp > height - padding - 15:
            break
        
        # Category dot
        cat = task.get("category", "default")
        cat_color = (*CATEGORY_COLORS.get(cat, (150, 150, 150)), 255)
        draw.ellipse([padding + 5, yp + 4, padding + 13, yp + 12], fill=cat_color)
        
        # Checkbox
        draw.rectangle([padding + 20, yp + 2, padding + 32, yp + 14],
                       outline=text_secondary, width=1)
        
        # Title
        title = task.get("title", "")
        max_chars = (width - 60) // int(base * 0.5)
        if len(title) > max_chars:
            title = title[:max_chars - 2] + ".."
        
        draw.text((padding + 40, yp), title, font=task_font, fill=text_color)
        yp += line_h
    
    if not upcoming:
        draw.text((padding, yp), "No tasks", font=task_font, fill=text_secondary)
    
    return glass_bg, (x, y)


def render_notes_widget(base_image: Image.Image, 
                        x: int, y: int, width: int, height: int,
                        settings: dict) -> Tuple[Image.Image, tuple]:
    """Render Notes widget with glass effect."""
    region = (x, y, x + width, y + height)
    notes_text = load_notes()
    
    glass_params = get_glass_params_for_region(base_image, region)
    colors = get_adaptive_colors(base_image, region)
    
    glass_bg = apply_glassmorphism(
        base_image, region,
        blur_radius=glass_params['blur_radius'],
        tint_color=glass_params['tint_color'],
        tint_opacity=glass_params['tint_opacity'],
        brightness=glass_params['brightness'],
        border_radius=15
    )
    
    draw = ImageDraw.Draw(glass_bg)
    
    text_color = (*colors['text'], 255)
    text_secondary = (*colors['text_secondary'], 255)
    
    base = max(width // 14, 11)
    padding = 15
    yp = padding + 5
    
    # Header
    header_font = get_font(int(base * 1.1), bold=True)
    draw_text_shadow(draw, (padding + 5, yp), "Notes", header_font, text_color)
    yp += int(base * 2)
    
    # Divider
    draw.line([(padding, yp), (width - padding, yp)], fill=(*text_secondary[:3], 60), width=1)
    yp += 12
    
    # Notes content
    notes_font = get_font(int(base * 0.8), bold=False)
    
    if notes_text:
        # Word wrap
        lines = []
        max_w = width - padding * 2 - 10
        
        for para in notes_text.split('\n'):
            words = para.split()
            line = ""
            for word in words:
                test = line + " " + word if line else word
                bbox = draw.textbbox((0, 0), test, font=notes_font)
                if bbox[2] - bbox[0] <= max_w:
                    line = test
                else:
                    if line:
                        lines.append(line)
                    line = word
            if line:
                lines.append(line)
            if not para:
                lines.append("")
        
        line_h = int(base * 1.3)
        max_lines = (height - yp - padding) // line_h
        
        for line in lines[:max_lines]:
            draw.text((padding + 5, yp), line, font=notes_font, fill=text_color)
            yp += line_h
    else:
        draw.text((padding + 5, yp), "Add notes in app...", font=notes_font, fill=text_secondary)
    
    return glass_bg, (x, y)


def render_clock_widget(base_image: Image.Image,
                        x: int, y: int, width: int, height: int,
                        settings: dict) -> Tuple[Image.Image, tuple]:
    """Render Clock widget with glass effect."""
    region = (x, y, x + width, y + height)
    
    glass_params = get_glass_params_for_region(base_image, region)
    colors = get_adaptive_colors(base_image, region)
    
    glass_bg = apply_glassmorphism(
        base_image, region,
        blur_radius=glass_params['blur_radius'],
        tint_color=glass_params['tint_color'],
        tint_opacity=glass_params['tint_opacity'],
        brightness=glass_params['brightness'],
        border_radius=15
    )
    
    draw = ImageDraw.Draw(glass_bg)
    text_color = (*colors['text'], 255)
    
    # Time
    time_str = datetime.now().strftime("%H:%M")
    base = max(width // 6, 20)
    time_font = get_font(int(base * 1.8), bold=True)
    
    draw_text_shadow(draw, (width // 2, height // 2), time_str, time_font, text_color)
    
    return glass_bg, (x, y)


# ============================================================================
# MAIN GENERATOR
# ============================================================================

def get_widget_position(base_size: tuple, widget_size: tuple,
                        x_percent: int, y_percent: int) -> Tuple[int, int]:
    """Calculate widget position from percentages."""
    base_w, base_h = base_size
    w_w, w_h = widget_size
    
    x = int((base_w - w_w) * x_percent / 100)
    y = int((base_h - w_h) * y_percent / 100)
    
    padding = 25
    x = max(padding, min(x, base_w - w_w - padding))
    y = max(padding, min(y, base_h - w_h - padding))
    
    return (x, y)


def generate_wallpaper(base_image_path: str, tasks: List[Dict], 
                       settings: dict = None) -> Optional[str]:
    """
    Generate wallpaper with smart-blending widgets.
    """
    if settings is None:
        settings = load_settings()
    
    try:
        base_img = Image.open(base_image_path).convert('RGBA')
        base_w, base_h = base_img.size
        result = base_img.copy()
        
        # Calendar Widget
        if settings.get("calendar_enabled", True):
            size_pct = settings.get("calendar_size_percent", 28)
            cal_w = int(base_w * size_pct / 100)
            cal_h = int(cal_w * 1.1)
            cal_w = max(260, min(cal_w, 480))
            cal_h = max(290, min(cal_h, 530))
            
            x_pct = settings.get("calendar_x_percent", 0)
            y_pct = settings.get("calendar_y_percent", 0)
            x, y = get_widget_position((base_w, base_h), (cal_w, cal_h), x_pct, y_pct)
            
            widget, pos = render_calendar_widget(result, tasks, x, y, cal_w, cal_h, settings)
            result.paste(widget, pos, widget)
        
        # To-Do Widget
        if settings.get("todo_enabled", True):
            w_pct = settings.get("todo_width_percent", 22)
            h_pct = settings.get("todo_height_percent", 40)
            todo_w = max(180, min(int(base_w * w_pct / 100), 380))
            todo_h = max(200, min(int(base_h * h_pct / 100), 480))
            
            x_pct = settings.get("todo_x_percent", 0)
            y_pct = settings.get("todo_y_percent", 55)
            x, y = get_widget_position((base_w, base_h), (todo_w, todo_h), x_pct, y_pct)
            
            widget, pos = render_todo_widget(result, tasks, x, y, todo_w, todo_h, settings)
            result.paste(widget, pos, widget)
        
        # Notes Widget
        if settings.get("notes_enabled", True):
            w_pct = settings.get("notes_width_percent", 22)
            h_pct = settings.get("notes_height_percent", 35)
            notes_w = max(180, min(int(base_w * w_pct / 100), 380))
            notes_h = max(150, min(int(base_h * h_pct / 100), 380))
            
            x_pct = settings.get("notes_x_percent", 75)
            y_pct = settings.get("notes_y_percent", 60)
            x, y = get_widget_position((base_w, base_h), (notes_w, notes_h), x_pct, y_pct)
            
            widget, pos = render_notes_widget(result, x, y, notes_w, notes_h, settings)
            result.paste(widget, pos, widget)
        
        # Clock Widget
        if settings.get("clock_enabled", False):
            size_pct = settings.get("clock_size_percent", 15)
            clock_w = max(120, min(int(base_w * size_pct / 100), 300))
            clock_h = int(clock_w * 0.5)
            
            x_pct = settings.get("clock_x_percent", 80)
            y_pct = settings.get("clock_y_percent", 5)
            x, y = get_widget_position((base_w, base_h), (clock_w, clock_h), x_pct, y_pct)
            
            widget, pos = render_clock_widget(result, x, y, clock_w, clock_h, settings)
            result.paste(widget, pos, widget)
        
        # Save
        output_path = OUTPUT_DIR / WALLPAPER_CONFIG["output_filename"]
        result.save(output_path, "PNG", quality=WALLPAPER_CONFIG["quality"])
        
        return str(output_path)
    
    except Exception as e:
        print(f"Error generating wallpaper: {e}")
        import traceback
        traceback.print_exc()
        return None
