"""
Wallpaper Generator - Premium Edition
Features: 4x Supersampled Text, Glassmorphism/Solid modes, DPI-Aware Scaling
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
# 4X SUPERSAMPLING TEXT RENDERING (Apple-smooth)
# ============================================================================

SUPERSAMPLE_SCALE = 4  # 4x for smooth antialiasing


def get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """Get system font with fallback."""
    fonts = ["Segoe UI Bold", "Segoe UI", "Arial Bold", "Arial"] if bold else ["Segoe UI", "Arial"]
    for name in fonts:
        try:
            return ImageFont.truetype(name, size)
        except:
            continue
    return ImageFont.load_default()


def render_smooth_text(text: str, font_size: int, color: tuple,
                       bold: bool = True, shadow_color: tuple = None,
                       shadow_offset: int = 2) -> Image.Image:
    """
    Render text at 4x resolution then downsample for smooth antialiasing.
    Returns transparent RGBA image cropped to text bounds.
    """
    # Load font at 4x size
    large_size = font_size * SUPERSAMPLE_SCALE
    font = get_font(large_size, bold)
    
    # Calculate text bounds
    temp_img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
    temp_draw = ImageDraw.Draw(temp_img)
    bbox = temp_draw.textbbox((0, 0), text, font=font)
    
    text_w = bbox[2] - bbox[0] + shadow_offset * SUPERSAMPLE_SCALE * 2
    text_h = bbox[3] - bbox[1] + shadow_offset * SUPERSAMPLE_SCALE * 2
    
    # Create large canvas
    large_img = Image.new('RGBA', (text_w + 20, text_h + 20), (0, 0, 0, 0))
    draw = ImageDraw.Draw(large_img)
    
    # Draw position (accounting for bbox offset)
    x = -bbox[0] + shadow_offset * SUPERSAMPLE_SCALE
    y = -bbox[1] + shadow_offset * SUPERSAMPLE_SCALE
    
    # Draw shadow at 4x
    if shadow_color:
        scaled_offset = shadow_offset * SUPERSAMPLE_SCALE
        for dx, dy in [(-scaled_offset, 0), (scaled_offset, 0), 
                       (0, -scaled_offset), (0, scaled_offset)]:
            draw.text((x + dx, y + dy), text, font=font, fill=shadow_color)
    
    # Draw main text at 4x
    draw.text((x, y), text, font=font, fill=color)
    
    # Downsample with high-quality LANCZOS
    final_w = text_w // SUPERSAMPLE_SCALE
    final_h = text_h // SUPERSAMPLE_SCALE
    
    result = large_img.resize((final_w + 5, final_h + 5), Image.Resampling.LANCZOS)
    
    return result


def draw_smooth_text(base_image: Image.Image, pos: tuple, text: str,
                     font_size: int, color: tuple, bold: bool = True,
                     shadow_color: tuple = None, shadow_offset: int = 2,
                     anchor: str = None):
    """
    Draw supersampled text onto base image.
    anchor: 'lt' (left-top), 'mt' (middle-top), 'mm' (middle-middle)
    """
    text_img = render_smooth_text(text, font_size, color, bold, shadow_color, shadow_offset)
    
    x, y = pos
    w, h = text_img.size
    
    # Handle anchors
    if anchor == 'mt':  # Middle-top
        x = x - w // 2
    elif anchor == 'mm':  # Middle-middle
        x = x - w // 2
        y = y - h // 2
    
    # Paste with transparency
    base_image.paste(text_img, (int(x), int(y)), text_img)


# ============================================================================
# DPI-AWARE SCALING
# ============================================================================

def calculate_dpi_scale(image_width: int, image_height: int) -> dict:
    """Calculate scaling factors based on image resolution."""
    REF_WIDTH = 1920
    aspect_ratio = image_width / image_height
    
    dpi_scale = min(image_width / REF_WIDTH, 2.0)
    dpi_scale = max(0.8, dpi_scale)
    
    if aspect_ratio > 2.0:
        width_factor = 0.10
    elif aspect_ratio > 1.7:
        width_factor = 0.12
    elif aspect_ratio > 1.5:
        width_factor = 0.15
    else:
        width_factor = 0.18
    
    return {
        'dpi_scale': dpi_scale,
        'width_factor': width_factor,
        'base_font': int(14 * dpi_scale),
        'padding': int(15 * dpi_scale),
        'border_radius': int(15 * dpi_scale),
    }


def calculate_widget_size(image_width: int, image_height: int,
                          widget_type: str, user_size_percent: int = 25) -> Tuple[int, int]:
    """Calculate optimal widget dimensions."""
    scale = calculate_dpi_scale(image_width, image_height)
    size_mult = 0.7 + (user_size_percent - 15) / 50
    
    if widget_type == 'calendar':
        base_w = int(image_width * scale['width_factor'] * size_mult)
        base_h = int(base_w * 1.1)
        base_w = max(220, min(base_w, int(image_width * 0.30)))
        base_h = max(250, min(base_h, int(image_height * 0.55)))
    elif widget_type == 'todo':
        base_w = int(image_width * scale['width_factor'] * 0.9 * size_mult)
        base_h = int(image_height * 0.4 * size_mult)
        base_w = max(180, min(base_w, int(image_width * 0.25)))
        base_h = max(180, min(base_h, int(image_height * 0.45)))
    elif widget_type == 'notes':
        base_w = int(image_width * scale['width_factor'] * 0.85 * size_mult)
        base_h = int(image_height * 0.35 * size_mult)
        base_w = max(160, min(base_w, int(image_width * 0.25)))
        base_h = max(140, min(base_h, int(image_height * 0.40)))
    elif widget_type == 'clock':
        base_w = int(image_width * 0.12 * size_mult)
        base_h = int(base_w * 0.45)
        base_w = max(100, min(base_w, int(image_width * 0.18)))
        base_h = max(50, min(base_h, int(image_height * 0.12)))
    else:
        base_w, base_h = 200, 200
    
    return (base_w, base_h)


def calculate_font_size(widget_width: int, widget_height: int,
                        font_role: str, dpi_scale: float = 1.0) -> int:
    """Calculate font size for widget."""
    base = min(widget_width, widget_height) / 12
    
    multipliers = {
        'large_date': 4.0, 'title': 1.4, 'header': 1.2,
        'body': 0.95, 'small': 0.75, 'weekday': 0.85, 'day': 0.9,
    }
    
    mult = multipliers.get(font_role, 1.0)
    size = int(base * mult * dpi_scale)
    
    min_sizes = {'large_date': 28, 'title': 12, 'header': 11, 'body': 10, 'small': 9}
    max_sizes = {'large_date': 80, 'title': 24, 'header': 20, 'body': 18, 'small': 14}
    
    return max(min_sizes.get(font_role, 9), min(size, max_sizes.get(font_role, 30)))


# ============================================================================
# WIDGET BACKGROUNDS: GLASS vs SOLID
# ============================================================================

def apply_glassmorphism(base_image: Image.Image, region: tuple,
                        blur_radius: int = 25, brightness: float = 1.0,
                        saturation: float = 1.1, tint_color: tuple = None,
                        tint_strength: float = 0.15, border_radius: int = 18) -> Image.Image:
    """True frosted glass effect."""
    x1, y1, x2, y2 = region
    w, h = x2 - x1, y2 - y1
    
    cropped = base_image.crop(region).convert('RGBA')
    blurred = cropped.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    
    if brightness != 1.0:
        blurred = ImageEnhance.Brightness(blurred).enhance(brightness)
    if saturation != 1.0:
        blurred = ImageEnhance.Color(blurred).enhance(saturation)
    blurred = ImageEnhance.Contrast(blurred).enhance(1.05)
    
    if tint_color:
        tint = Image.new('RGBA', (w, h), (*tint_color, int(255 * tint_strength)))
        blurred = Image.alpha_composite(blurred, tint)
    
    # Border highlight
    draw = ImageDraw.Draw(blurred)
    draw.rounded_rectangle([0, 0, w-1, h-1], radius=border_radius,
                           outline=(255, 255, 255, 25), width=1)
    
    # Rounded mask
    mask = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w, h], radius=border_radius, fill=255)
    blurred.putalpha(mask)
    
    return blurred


def apply_solid_background(width: int, height: int, theme: dict,
                           opacity: int = 220, border_radius: int = 18) -> Image.Image:
    """Old-style solid color background."""
    bg_color = (*theme['bg_color'], opacity)
    
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    draw.rounded_rectangle([0, 0, width, height], radius=border_radius, fill=bg_color)
    
    # Subtle border
    border_color = (*theme.get('border_color', theme['bg_color']), 80)
    draw.rounded_rectangle([0, 0, width-1, height-1], radius=border_radius,
                           outline=border_color, width=1)
    
    return img


def get_optimal_glass_params(image: Image.Image, region: tuple) -> dict:
    """Analyze region for optimal glass effect."""
    cropped = image.crop(region).convert('L')
    brightness = np.mean(np.array(cropped)) / 255.0
    
    if brightness < 0.35:
        return {'blur_radius': 28, 'brightness': 1.3, 'saturation': 1.2,
                'tint_color': (220, 220, 230), 'tint_strength': 0.12}
    elif brightness > 0.65:
        return {'blur_radius': 25, 'brightness': 0.75, 'saturation': 1.1,
                'tint_color': (30, 30, 40), 'tint_strength': 0.18}
    else:
        return {'blur_radius': 26, 'brightness': 1.05, 'saturation': 1.15,
                'tint_color': (255, 255, 255), 'tint_strength': 0.12}


def get_adaptive_colors(image: Image.Image, region: tuple, use_glass: bool = True) -> dict:
    """Get optimal text colors based on background."""
    cropped = image.crop(region).convert('L')
    avg_brightness = np.mean(np.array(cropped)) / 255.0
    
    # For solid mode, use theme colors; for glass, adapt to image
    if avg_brightness < 0.45 or use_glass:
        text = (255, 255, 255)
        text_secondary = (200, 200, 210)
        shadow = (0, 0, 0, 120)
    else:
        text = (35, 35, 40)
        text_secondary = (80, 80, 90)
        shadow = (255, 255, 255, 60)
    
    # Generate accent
    import colorsys
    color_crop = image.crop(region).convert('RGB').resize((30, 30))
    dominant = tuple(map(int, np.mean(np.array(color_crop).reshape(-1, 3), axis=0)))
    
    r, g, b = [x / 255.0 for x in dominant]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    
    h_accent = (h + 0.45) % 1.0
    s_accent = min(1.0, s * 1.5 + 0.3)
    r, g, b = colorsys.hls_to_rgb(h_accent, 0.55, s_accent)
    accent = (int(r * 255), int(g * 255), int(b * 255))
    
    h_today = (h + 0.3) % 1.0
    r, g, b = colorsys.hls_to_rgb(h_today, 0.5, 0.8)
    today = (int(r * 255), int(g * 255), int(b * 255))
    
    return {'text': text, 'text_secondary': text_secondary, 'shadow': shadow,
            'accent': accent, 'today': today, 'brightness': avg_brightness}


# ============================================================================
# WIDGET RENDERERS WITH SUPERSAMPLED TEXT
# ============================================================================

def render_calendar_widget(base_image: Image.Image, tasks: List[Dict],
                           x: int, y: int, width: int, height: int,
                           settings: dict, scale: dict, theme: dict) -> Tuple[Image.Image, tuple]:
    """Render calendar with smooth text."""
    region = (x, y, x + width, y + height)
    use_glass = settings.get('blend_mode', 'glass') == 'glass'
    
    if use_glass:
        glass_params = get_optimal_glass_params(base_image, region)
        widget = apply_glassmorphism(base_image, region, border_radius=scale['border_radius'],
                                      **glass_params)
    else:
        widget = apply_solid_background(width, height, theme, 
                                         opacity=int(settings.get('opacity', 90) * 255 / 100),
                                         border_radius=scale['border_radius'])
    
    colors = get_adaptive_colors(base_image, region, use_glass)
    if not use_glass:
        colors['text'] = theme['text_color']
        colors['text_secondary'] = theme['text_secondary']
        colors['today'] = theme['today_color']
        colors['shadow'] = None
    
    text_color = (*colors['text'], 255)
    text_secondary = (*colors['text_secondary'], 255)
    accent = (*colors['accent'], 255)
    today_color = (*colors['today'], 255)
    shadow = colors['shadow']
    
    padding = scale['padding']
    yp = padding
    today = datetime.now()
    
    style = settings.get('calendar_style', 'aesthetic')
    
    # Large date (aesthetic mode)
    if style not in ['compact', 'minimal']:
        large_size = calculate_font_size(width, height, 'large_date', scale['dpi_scale'])
        day_str = f"{today.day:02d}"
        draw_smooth_text(widget, (padding + 5, yp), day_str, large_size, text_color,
                         bold=True, shadow_color=shadow)
        
        # Month/year
        month_size = calculate_font_size(width, height, 'title', scale['dpi_scale'])
        mx = padding + int(large_size * 1.3)
        draw_smooth_text(widget, (mx, yp + 5), calendar.month_name[today.month],
                         month_size, text_secondary, bold=False)
        draw_smooth_text(widget, (mx, yp + month_size + 8), str(today.year),
                         int(month_size * 0.85), text_secondary, bold=False)
        
        yp += int(large_size * 1.1)
    else:
        # Compact header
        header_size = calculate_font_size(width, height, 'header', scale['dpi_scale'])
        header_text = f"{calendar.month_abbr[today.month]} {today.day}, {today.year}"
        draw_smooth_text(widget, (padding, yp), header_text, header_size, text_color,
                         bold=True, shadow_color=shadow)
        yp += int(header_size * 1.8)
    
    # Divider
    draw = ImageDraw.Draw(widget)
    draw.line([(padding, yp), (width - padding, yp)], fill=(*text_secondary[:3], 60), width=1)
    yp += 10
    
    # Weekdays
    weekdays = ["S", "M", "T", "W", "T", "F", "S"]
    cell_w = (width - padding * 2) // 7
    wd_size = calculate_font_size(width, height, 'weekday', scale['dpi_scale'])
    
    for i, wd in enumerate(weekdays):
        wx = padding + i * cell_w + cell_w // 2
        col = accent if i == 0 else text_secondary
        draw_smooth_text(widget, (wx, yp), wd, wd_size, col, bold=True, anchor='mt')
    
    yp += int(wd_size * 1.6)
    
    # Calendar grid
    cal = calendar.Calendar(firstweekday=6)
    month_days = cal.monthdayscalendar(today.year, today.month)
    
    tasks_by_date = {}
    for t in tasks:
        d = t.get("date", "")
        if d not in tasks_by_date:
            tasks_by_date[d] = []
        tasks_by_date[d].append(t)
    
    day_size = calculate_font_size(width, height, 'day', scale['dpi_scale'])
    cell_h = int(day_size * 1.6)
    
    max_weeks = 5 if style in ['compact', 'minimal'] else 6
    
    for week in month_days[:max_weeks]:
        for i, day in enumerate(week):
            if day == 0:
                continue
            
            cx = padding + i * cell_w + cell_w // 2
            date_str = f"{today.year}-{today.month:02d}-{day:02d}"
            has_tasks = date_str in tasks_by_date
            
            if day == today.day:
                r = int(day_size * 0.75)
                draw.ellipse([cx - r, yp - r + 4, cx + r, yp + r + 4], fill=today_color)
                day_text_col = (255, 255, 255, 255)
            elif i == 0:
                day_text_col = accent
            else:
                day_text_col = text_color
            
            draw_smooth_text(widget, (cx, yp + 4), str(day), day_size, day_text_col,
                             bold=False, anchor='mt')
            
            if has_tasks and day != today.day:
                for j, task in enumerate(tasks_by_date[date_str][:2]):
                    cat = task.get("category", "default")
                    dot_col = (*CATEGORY_COLORS.get(cat, (150, 150, 150)), 255)
                    dx = cx - 3 + j * 6
                    draw.ellipse([dx - 2, yp + day_size + 3, dx + 2, yp + day_size + 7], fill=dot_col)
        
        yp += cell_h
    
    return widget, (x, y)


def render_todo_widget(base_image: Image.Image, tasks: List[Dict],
                       x: int, y: int, width: int, height: int,
                       settings: dict, scale: dict, theme: dict) -> Tuple[Image.Image, tuple]:
    """Render To-Do with smooth text."""
    region = (x, y, x + width, y + height)
    use_glass = settings.get('blend_mode', 'glass') == 'glass'
    
    if use_glass:
        glass_params = get_optimal_glass_params(base_image, region)
        widget = apply_glassmorphism(base_image, region, border_radius=scale['border_radius'],
                                      **glass_params)
    else:
        widget = apply_solid_background(width, height, theme,
                                         opacity=int(settings.get('opacity', 85) * 255 / 100),
                                         border_radius=scale['border_radius'])
    
    colors = get_adaptive_colors(base_image, region, use_glass)
    if not use_glass:
        colors['text'] = theme['text_color']
        colors['text_secondary'] = theme['text_secondary']
        colors['shadow'] = None
    
    text_color = (*colors['text'], 255)
    text_secondary = (*colors['text_secondary'], 255)
    shadow = colors['shadow']
    
    draw = ImageDraw.Draw(widget)
    padding = scale['padding']
    yp = padding
    
    # Header
    header_size = calculate_font_size(width, height, 'header', scale['dpi_scale'])
    draw_smooth_text(widget, (padding, yp), "To Do", header_size, text_color,
                     bold=True, shadow_color=shadow)
    yp += int(header_size * 1.8)
    
    draw.line([(padding, yp), (width - padding, yp)], fill=(*text_secondary[:3], 60), width=1)
    yp += 8
    
    # Tasks
    today_date = datetime.now().date()
    upcoming = []
    for task in tasks:
        try:
            task_date = datetime.strptime(task["date"], "%Y-%m-%d").date()
            delta = (task_date - today_date).days
            if -1 <= delta <= 7:
                upcoming.append((delta, task))
        except:
            continue
    upcoming.sort(key=lambda x: x[0])
    
    body_size = calculate_font_size(width, height, 'body', scale['dpi_scale'])
    line_h = int(body_size * 1.5)
    max_tasks = (height - yp - padding) // line_h
    
    for delta, task in upcoming[:max_tasks]:
        if yp > height - padding - 10:
            break
        
        cat = task.get("category", "default")
        cat_color = (*CATEGORY_COLORS.get(cat, (150, 150, 150)), 255)
        draw.ellipse([padding, yp + 3, padding + 8, yp + 11], fill=cat_color)
        draw.rectangle([padding + 14, yp + 1, padding + 24, yp + 11],
                       outline=text_secondary, width=1)
        
        title = task.get("title", "")
        max_chars = (width - 45) // int(body_size * 0.55)
        if len(title) > max_chars:
            title = title[:max_chars - 2] + ".."
        
        draw_smooth_text(widget, (padding + 30, yp - 1), title, body_size, text_color, bold=False)
        yp += line_h
    
    if not upcoming:
        draw_smooth_text(widget, (padding, yp), "No tasks", body_size, text_secondary, bold=False)
    
    return widget, (x, y)


def render_notes_widget(base_image: Image.Image,
                        x: int, y: int, width: int, height: int,
                        settings: dict, scale: dict, theme: dict) -> Tuple[Image.Image, tuple]:
    """Render Notes with smooth text."""
    region = (x, y, x + width, y + height)
    notes_text = load_notes()
    use_glass = settings.get('blend_mode', 'glass') == 'glass'
    
    if use_glass:
        glass_params = get_optimal_glass_params(base_image, region)
        widget = apply_glassmorphism(base_image, region, border_radius=scale['border_radius'],
                                      **glass_params)
    else:
        widget = apply_solid_background(width, height, theme,
                                         opacity=int(settings.get('opacity', 85) * 255 / 100),
                                         border_radius=scale['border_radius'])
    
    colors = get_adaptive_colors(base_image, region, use_glass)
    if not use_glass:
        colors['text'] = theme['text_color']
        colors['text_secondary'] = theme['text_secondary']
        colors['shadow'] = None
    
    text_color = (*colors['text'], 255)
    text_secondary = (*colors['text_secondary'], 255)
    shadow = colors['shadow']
    
    draw = ImageDraw.Draw(widget)
    padding = scale['padding']
    yp = padding
    
    header_size = calculate_font_size(width, height, 'header', scale['dpi_scale'])
    draw_smooth_text(widget, (padding, yp), "Notes", header_size, text_color,
                     bold=True, shadow_color=shadow)
    yp += int(header_size * 1.8)
    
    draw.line([(padding, yp), (width - padding, yp)], fill=(*text_secondary[:3], 60), width=1)
    yp += 10
    
    body_size = calculate_font_size(width, height, 'body', scale['dpi_scale'])
    
    if notes_text:
        # Simple word wrap
        font = get_font(body_size, bold=False)
        lines = []
        max_w = width - padding * 2
        
        for para in notes_text.split('\n'):
            words = para.split()
            line = ""
            for word in words:
                test = line + " " + word if line else word
                bbox = draw.textbbox((0, 0), test, font=font)
                if bbox[2] - bbox[0] <= max_w:
                    line = test
                else:
                    if line:
                        lines.append(line)
                    line = word
            if line:
                lines.append(line)
        
        line_h = int(body_size * 1.35)
        max_lines = (height - yp - padding) // line_h
        
        for line in lines[:max_lines]:
            draw_smooth_text(widget, (padding, yp), line, body_size, text_color, bold=False)
            yp += line_h
    else:
        draw_smooth_text(widget, (padding, yp), "Add notes...", body_size, text_secondary, bold=False)
    
    return widget, (x, y)


def render_clock_widget(base_image: Image.Image,
                        x: int, y: int, width: int, height: int,
                        settings: dict, scale: dict, theme: dict) -> Tuple[Image.Image, tuple]:
    """Render Clock with smooth text."""
    region = (x, y, x + width, y + height)
    use_glass = settings.get('blend_mode', 'glass') == 'glass'
    
    if use_glass:
        glass_params = get_optimal_glass_params(base_image, region)
        widget = apply_glassmorphism(base_image, region, border_radius=scale['border_radius'],
                                      **glass_params)
    else:
        widget = apply_solid_background(width, height, theme,
                                         opacity=int(settings.get('opacity', 90) * 255 / 100),
                                         border_radius=scale['border_radius'])
    
    colors = get_adaptive_colors(base_image, region, use_glass)
    if not use_glass:
        colors['text'] = theme['text_color']
        colors['shadow'] = None
    
    text_color = (*colors['text'], 255)
    shadow = colors['shadow']
    
    time_str = datetime.now().strftime("%H:%M")
    time_size = calculate_font_size(width, height, 'large_date', scale['dpi_scale'])
    
    draw_smooth_text(widget, (width // 2, height // 2), time_str, time_size,
                     text_color, bold=True, shadow_color=shadow, anchor='mm')
    
    return widget, (x, y)


# ============================================================================
# MAIN GENERATOR
# ============================================================================

def get_widget_position(base_size: tuple, widget_size: tuple,
                        x_percent: int, y_percent: int) -> Tuple[int, int]:
    base_w, base_h = base_size
    w_w, w_h = widget_size
    
    x = int((base_w - w_w) * x_percent / 100)
    y = int((base_h - w_h) * y_percent / 100)
    
    padding = 30
    return (max(padding, min(x, base_w - w_w - padding)),
            max(padding, min(y, base_h - w_h - padding)))


def generate_wallpaper(base_image_path: str, tasks: List[Dict],
                       settings: dict = None) -> Optional[str]:
    """Generate wallpaper with premium smooth text."""
    if settings is None:
        settings = load_settings()
    
    try:
        base_img = Image.open(base_image_path).convert('RGBA')
        base_w, base_h = base_img.size
        
        scale = calculate_dpi_scale(base_w, base_h)
        theme = get_theme(settings.get('theme', 'dark'))
        result = base_img.copy()
        
        # Calendar
        if settings.get("calendar_enabled", True):
            size_pct = settings.get("calendar_size_percent", 25)
            cal_w, cal_h = calculate_widget_size(base_w, base_h, 'calendar', size_pct)
            x, y = get_widget_position((base_w, base_h), (cal_w, cal_h),
                                        settings.get("calendar_x_percent", 0),
                                        settings.get("calendar_y_percent", 0))
            widget, pos = render_calendar_widget(result, tasks, x, y, cal_w, cal_h, settings, scale, theme)
            result.paste(widget, pos, widget)
        
        # To-Do
        if settings.get("todo_enabled", True):
            size_pct = settings.get("todo_width_percent", 22)
            todo_w, todo_h = calculate_widget_size(base_w, base_h, 'todo', size_pct)
            x, y = get_widget_position((base_w, base_h), (todo_w, todo_h),
                                        settings.get("todo_x_percent", 0),
                                        settings.get("todo_y_percent", 55))
            widget, pos = render_todo_widget(result, tasks, x, y, todo_w, todo_h, settings, scale, theme)
            result.paste(widget, pos, widget)
        
        # Notes
        if settings.get("notes_enabled", True):
            size_pct = settings.get("notes_width_percent", 22)
            notes_w, notes_h = calculate_widget_size(base_w, base_h, 'notes', size_pct)
            x, y = get_widget_position((base_w, base_h), (notes_w, notes_h),
                                        settings.get("notes_x_percent", 75),
                                        settings.get("notes_y_percent", 60))
            widget, pos = render_notes_widget(result, x, y, notes_w, notes_h, settings, scale, theme)
            result.paste(widget, pos, widget)
        
        # Clock
        if settings.get("clock_enabled", False):
            size_pct = settings.get("clock_size_percent", 15)
            clock_w, clock_h = calculate_widget_size(base_w, base_h, 'clock', size_pct)
            x, y = get_widget_position((base_w, base_h), (clock_w, clock_h),
                                        settings.get("clock_x_percent", 80),
                                        settings.get("clock_y_percent", 5))
            widget, pos = render_clock_widget(result, x, y, clock_w, clock_h, settings, scale, theme)
            result.paste(widget, pos, widget)
        
        output_path = OUTPUT_DIR / WALLPAPER_CONFIG["output_filename"]
        result.save(output_path, "PNG", quality=WALLPAPER_CONFIG["quality"])
        
        return str(output_path)
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None
