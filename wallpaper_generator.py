"""
Wallpaper Generator - Smart Blending with DPI-Aware Scaling
Features: Glassmorphism, Adaptive Colors, Resolution-Aware Sizing, Compact Modes
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
# SOLUTION 1: DPI-AWARE SCALING
# ============================================================================

def calculate_dpi_scale(image_width: int, image_height: int) -> dict:
    """
    Calculate scaling factors based on image resolution and aspect ratio.
    
    Returns scaling parameters that ensure widgets look proportional
    on any screen size from 1080p to 4K ultrawide.
    """
    # Reference resolution (1920x1080 as baseline)
    REF_WIDTH = 1920
    REF_HEIGHT = 1080
    
    # Calculate actual ratio
    aspect_ratio = image_width / image_height
    total_pixels = image_width * image_height
    
    # DPI scale factor (relative to 1080p)
    # 4K = 2x, 1440p = 1.33x, 1080p = 1x
    dpi_scale = min(image_width / REF_WIDTH, image_height / REF_HEIGHT)
    dpi_scale = max(0.8, min(dpi_scale, 2.0))  # Clamp between 0.8 and 2.0
    
    # Aspect ratio adjustments
    # Ultrawide (21:9) = narrower widgets
    # Portrait = shorter, wider widgets
    if aspect_ratio > 2.0:  # Ultra-ultrawide (32:9)
        width_factor = 0.10
        height_factor = 0.40
    elif aspect_ratio > 1.7:  # Ultrawide (21:9)
        width_factor = 0.12
        height_factor = 0.45
    elif aspect_ratio > 1.5:  # Standard widescreen (16:9)
        width_factor = 0.15
        height_factor = 0.50
    elif aspect_ratio > 1.2:  # 4:3 / 3:2
        width_factor = 0.18
        height_factor = 0.45
    else:  # Portrait or square
        width_factor = 0.25
        height_factor = 0.35
    
    # Base font size (scales with resolution)
    base_font = int(14 * dpi_scale)
    base_font = max(11, min(base_font, 22))  # Clamp
    
    return {
        'dpi_scale': dpi_scale,
        'aspect_ratio': aspect_ratio,
        'width_factor': width_factor,
        'height_factor': height_factor,
        'base_font': base_font,
        'padding': int(15 * dpi_scale),
        'border_radius': int(15 * dpi_scale),
    }


def calculate_widget_size(image_width: int, image_height: int, 
                          widget_type: str, user_size_percent: int = 25) -> Tuple[int, int]:
    """
    Calculate optimal widget dimensions based on image resolution.
    
    Args:
        image_width, image_height: Wallpaper dimensions
        widget_type: 'calendar', 'todo', 'notes', 'clock'
        user_size_percent: User's slider value (0-100 maps to size range)
    """
    scale = calculate_dpi_scale(image_width, image_height)
    
    # User percent (15-45 slider) maps to a multiplier (0.7 to 1.3)
    size_mult = 0.7 + (user_size_percent - 15) / 50  # Maps 15->0.7, 45->1.3
    
    if widget_type == 'calendar':
        # Calendar: width is % of screen, height is proportional
        base_w = int(image_width * scale['width_factor'] * size_mult)
        base_h = int(base_w * 1.1)  # Slightly taller than wide
        
        # Absolute limits
        base_w = max(220, min(base_w, int(image_width * 0.30)))
        base_h = max(250, min(base_h, int(image_height * 0.55)))
        
    elif widget_type == 'todo':
        base_w = int(image_width * scale['width_factor'] * 0.9 * size_mult)
        base_h = int(image_height * scale['height_factor'] * 0.8 * size_mult)
        
        base_w = max(180, min(base_w, int(image_width * 0.25)))
        base_h = max(180, min(base_h, int(image_height * 0.45)))
        
    elif widget_type == 'notes':
        base_w = int(image_width * scale['width_factor'] * 0.85 * size_mult)
        base_h = int(image_height * scale['height_factor'] * 0.7 * size_mult)
        
        base_w = max(160, min(base_w, int(image_width * 0.25)))
        base_h = max(140, min(base_h, int(image_height * 0.40)))
        
    elif widget_type == 'clock':
        base_w = int(image_width * 0.12 * size_mult)
        base_h = int(base_w * 0.45)
        
        base_w = max(100, min(base_w, int(image_width * 0.18)))
        base_h = max(50, min(base_h, int(image_height * 0.12)))
    else:
        base_w = 200
        base_h = 200
    
    return (base_w, base_h)


def calculate_font_size(widget_width: int, widget_height: int, 
                        font_role: str, dpi_scale: float = 1.0) -> int:
    """
    Calculate font size that fills the widget properly without excess padding.
    
    font_role: 'title', 'header', 'body', 'small', 'large_date'
    """
    # Base size relative to widget dimensions
    base = min(widget_width, widget_height) / 12
    
    multipliers = {
        'large_date': 4.0,
        'title': 1.4,
        'header': 1.2,
        'body': 0.95,
        'small': 0.75,
        'weekday': 0.85,
        'day': 0.9,
    }
    
    mult = multipliers.get(font_role, 1.0)
    size = int(base * mult * dpi_scale)
    
    # Clamp to reasonable range
    min_sizes = {'large_date': 28, 'title': 12, 'header': 11, 'body': 10, 'small': 9}
    max_sizes = {'large_date': 80, 'title': 24, 'header': 20, 'body': 18, 'small': 14}
    
    size = max(min_sizes.get(font_role, 9), min(size, max_sizes.get(font_role, 30)))
    return size


# ============================================================================
# SOLUTION 2: TRUE GLASSMORPHISM
# ============================================================================

def apply_glassmorphism(base_image: Image.Image, region: tuple,
                        blur_radius: int = 25,
                        brightness: float = 1.0,
                        saturation: float = 1.1,
                        tint_color: tuple = None,
                        tint_strength: float = 0.15,
                        border_radius: int = 18) -> Image.Image:
    """
    True frosted glass effect:
    1. Crop background region
    2. Apply Gaussian blur
    3. Adjust brightness/contrast
    4. Add subtle tint overlay
    5. Apply rounded corners
    
    Returns the glass panel as RGBA with transparency mask.
    """
    x1, y1, x2, y2 = region
    w, h = x2 - x1, y2 - y1
    
    # Step 1: Crop the actual background
    cropped = base_image.crop(region).convert('RGBA')
    
    # Step 2: Heavy blur (the "frosted" effect)
    blurred = cropped.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    
    # Step 3: Brightness adjustment
    if brightness != 1.0:
        enhancer = ImageEnhance.Brightness(blurred)
        blurred = enhancer.enhance(brightness)
    
    # Step 4: Saturation boost (makes colors pop through the blur)
    if saturation != 1.0:
        enhancer = ImageEnhance.Color(blurred)
        blurred = enhancer.enhance(saturation)
    
    # Step 5: Subtle contrast boost
    enhancer = ImageEnhance.Contrast(blurred)
    blurred = enhancer.enhance(1.05)
    
    # Step 6: Apply tint overlay
    if tint_color:
        tint_layer = Image.new('RGBA', (w, h), (*tint_color, int(255 * tint_strength)))
        blurred = Image.alpha_composite(blurred, tint_layer)
    
    # Step 7: Add subtle inner border for depth
    draw = ImageDraw.Draw(blurred)
    # Light edge at top-left
    draw.rounded_rectangle([0, 0, w-1, h-1], radius=border_radius,
                           outline=(255, 255, 255, 30), width=1)
    
    # Step 8: Create rounded corner mask
    mask = Image.new('L', (w, h), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([0, 0, w, h], radius=border_radius, fill=255)
    
    # Apply mask
    blurred.putalpha(mask)
    
    return blurred


def get_optimal_glass_params(image: Image.Image, region: tuple) -> dict:
    """
    Analyze the region and return optimal glass parameters.
    """
    cropped = image.crop(region).convert('L')
    brightness = np.mean(np.array(cropped)) / 255.0
    
    # Also check variance (busy vs calm areas)
    variance = np.var(np.array(cropped)) / (255 ** 2)
    is_busy = variance > 0.02
    
    if brightness < 0.35:  # Dark background
        return {
            'blur_radius': 30 if is_busy else 25,
            'brightness': 1.3,
            'saturation': 1.2,
            'tint_color': (220, 220, 230),
            'tint_strength': 0.12,
        }
    elif brightness > 0.65:  # Light background
        return {
            'blur_radius': 28 if is_busy else 22,
            'brightness': 0.75,
            'saturation': 1.1,
            'tint_color': (30, 30, 40),
            'tint_strength': 0.18,
        }
    else:  # Mid-tone
        return {
            'blur_radius': 26,
            'brightness': 1.05,
            'saturation': 1.15,
            'tint_color': (255, 255, 255),
            'tint_strength': 0.12,
        }


# ============================================================================
# SOLUTION 4: AUTO-CONTRAST TEXT COLORING
# ============================================================================

def get_adaptive_text_colors(image: Image.Image, region: tuple) -> dict:
    """
    Analyze wallpaper region and return optimal text colors.
    White text on dark, black text on light.
    """
    cropped = image.crop(region).convert('L')
    avg_brightness = np.mean(np.array(cropped)) / 255.0
    
    # Also get color info for accent
    color_crop = image.crop(region).convert('RGB')
    color_crop_small = color_crop.resize((50, 50))
    pixels = np.array(color_crop_small).reshape(-1, 3)
    dominant = tuple(map(int, np.mean(pixels, axis=0)))
    
    if avg_brightness < 0.45:
        # Dark background -> light text
        text_primary = (255, 255, 255)
        text_secondary = (200, 200, 210)
        shadow_color = (0, 0, 0, 120)
    elif avg_brightness > 0.55:
        # Light background -> dark text
        text_primary = (35, 35, 40)
        text_secondary = (80, 80, 90)
        shadow_color = (255, 255, 255, 80)
    else:
        # Mid-tone -> white with stronger shadow
        text_primary = (255, 255, 255)
        text_secondary = (220, 220, 230)
        shadow_color = (0, 0, 0, 150)
    
    # Generate accent from dominant color
    import colorsys
    r, g, b = [x / 255.0 for x in dominant]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    
    # Shift hue for accent
    h_accent = (h + 0.45) % 1.0
    s_accent = min(1.0, s * 1.5 + 0.3)
    l_accent = max(0.45, min(0.6, l))
    
    r, g, b = colorsys.hls_to_rgb(h_accent, l_accent, s_accent)
    accent = (int(r * 255), int(g * 255), int(b * 255))
    
    # Today highlight - vibrant
    h_today = (h + 0.3) % 1.0
    r, g, b = colorsys.hls_to_rgb(h_today, 0.5, 0.8)
    today_color = (int(r * 255), int(g * 255), int(b * 255))
    
    return {
        'text': text_primary,
        'text_secondary': text_secondary,
        'shadow': shadow_color,
        'accent': accent,
        'today': today_color,
        'brightness': avg_brightness
    }


# ============================================================================
# FONT UTILITIES
# ============================================================================

def get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    fonts = ["Segoe UI Bold", "Segoe UI", "Arial Bold", "Arial"] if bold else ["Segoe UI", "Arial"]
    for name in fonts:
        try:
            return ImageFont.truetype(name, size)
        except:
            continue
    return ImageFont.load_default()


def draw_text_shadow(draw, pos, text, font, fill, shadow_color=(0,0,0,100), offset=2, anchor=None):
    x, y = pos
    kwargs = {'anchor': anchor} if anchor else {}
    for dx, dy in [(-offset, 0), (offset, 0), (0, -offset), (0, offset)]:
        draw.text((x + dx, y + dy), text, font=font, fill=shadow_color, **kwargs)
    draw.text(pos, text, font=font, fill=fill, **kwargs)


# ============================================================================
# SOLUTION 3: COMPACT CALENDAR MODE
# ============================================================================

def render_calendar_compact(glass_bg: Image.Image, tasks: List[Dict],
                            width: int, height: int, colors: dict, 
                            scale: dict) -> Image.Image:
    """
    Compact calendar: horizontal strip or mini-grid without excess padding.
    Shows current week prominently instead of full month grid.
    """
    draw = ImageDraw.Draw(glass_bg)
    
    text_color = (*colors['text'], 255)
    text_secondary = (*colors['text_secondary'], 255)
    accent = (*colors['accent'], 255)
    today_color = (*colors['today'], 255)
    
    padding = scale['padding']
    yp = padding
    
    today = datetime.now()
    
    # Header: Month + Day in one line
    header_size = calculate_font_size(width, height, 'header', scale['dpi_scale'])
    header_font = get_font(header_size, bold=True)
    
    header_text = f"{calendar.month_abbr[today.month]} {today.day}, {today.year}"
    draw_text_shadow(draw, (padding, yp), header_text, header_font, text_color, colors['shadow'])
    yp += int(header_size * 1.8)
    
    # Weekday headers - compact single row
    weekdays = ["S", "M", "T", "W", "T", "F", "S"]
    cell_w = (width - padding * 2) // 7
    wd_size = calculate_font_size(width, height, 'weekday', scale['dpi_scale'])
    wd_font = get_font(wd_size, bold=True)
    
    for i, wd in enumerate(weekdays):
        wx = padding + i * cell_w + cell_w // 2
        col = accent if i == 0 else text_secondary
        draw.text((wx, yp), wd, font=wd_font, fill=col, anchor="mt")
    
    yp += int(wd_size * 1.5)
    
    # Days grid - compact
    cal = calendar.Calendar(firstweekday=6)
    month_days = cal.monthdayscalendar(today.year, today.month)
    
    tasks_by_date = {}
    for t in tasks:
        d = t.get("date", "")
        if d not in tasks_by_date:
            tasks_by_date[d] = []
        tasks_by_date[d].append(t)
    
    day_size = calculate_font_size(width, height, 'day', scale['dpi_scale'])
    day_font = get_font(day_size, bold=False)
    cell_h = int(day_size * 1.5)  # Tight spacing
    
    # Only show up to 5 weeks to keep it compact
    for week in month_days[:5]:
        for i, day in enumerate(week):
            if day == 0:
                continue
            
            cx = padding + i * cell_w + cell_w // 2
            date_str = f"{today.year}-{today.month:02d}-{day:02d}"
            has_tasks = date_str in tasks_by_date
            
            if day == today.day:
                r = int(day_size * 0.7)
                draw.ellipse([cx - r, yp - r + 3, cx + r, yp + r + 3], fill=today_color)
                day_text_col = (255, 255, 255, 255)
            elif i == 0:
                day_text_col = accent
            else:
                day_text_col = text_color
            
            draw.text((cx, yp + 3), str(day), font=day_font, fill=day_text_col, anchor="mt")
            
            # Dot for tasks
            if has_tasks and day != today.day:
                draw.ellipse([cx - 2, yp + day_size + 2, cx + 2, yp + day_size + 6], 
                            fill=accent)
        
        yp += cell_h
    
    return glass_bg


def render_calendar_full(glass_bg: Image.Image, tasks: List[Dict],
                         width: int, height: int, colors: dict,
                         scale: dict, style: str = 'aesthetic') -> Image.Image:
    """
    Full calendar with large date display (aesthetic mode).
    """
    draw = ImageDraw.Draw(glass_bg)
    
    text_color = (*colors['text'], 255)
    text_secondary = (*colors['text_secondary'], 255)
    accent = (*colors['accent'], 255)
    today_color = (*colors['today'], 255)
    
    padding = scale['padding']
    yp = padding
    
    today = datetime.now()
    
    # Large date number
    large_size = calculate_font_size(width, height, 'large_date', scale['dpi_scale'])
    large_font = get_font(large_size, bold=True)
    day_str = f"{today.day:02d}"
    draw_text_shadow(draw, (padding + 5, yp), day_str, large_font, text_color, colors['shadow'])
    
    # Month/Year next to large date
    month_size = calculate_font_size(width, height, 'title', scale['dpi_scale'])
    month_font = get_font(month_size, bold=False)
    
    mx = padding + int(large_size * 1.3)
    draw.text((mx, yp + 5), calendar.month_name[today.month], font=month_font, fill=text_secondary)
    
    small_font = get_font(int(month_size * 0.85), bold=False)
    draw.text((mx, yp + month_size + 8), str(today.year), font=small_font, fill=text_secondary)
    
    yp += int(large_size * 1.1)
    
    # Divider
    draw.line([(padding, yp), (width - padding, yp)], fill=(*text_secondary[:3], 60), width=1)
    yp += 10
    
    # Weekdays
    weekdays = ["S", "M", "T", "W", "T", "F", "S"]
    cell_w = (width - padding * 2) // 7
    wd_size = calculate_font_size(width, height, 'weekday', scale['dpi_scale'])
    wd_font = get_font(wd_size, bold=True)
    
    for i, wd in enumerate(weekdays):
        wx = padding + i * cell_w + cell_w // 2
        col = accent if i == 0 else text_secondary
        draw.text((wx, yp), wd, font=wd_font, fill=col, anchor="mt")
    
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
    day_font = get_font(day_size, bold=False)
    cell_h = int(day_size * 1.6)
    
    for week in month_days[:6]:
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
            
            draw.text((cx, yp + 4), str(day), font=day_font, fill=day_text_col, anchor="mt")
            
            if has_tasks and day != today.day:
                tasks_list = tasks_by_date[date_str]
                for j, task in enumerate(tasks_list[:2]):
                    cat = task.get("category", "default")
                    dot_col = (*CATEGORY_COLORS.get(cat, (150, 150, 150)), 255)
                    dx = cx - 3 + j * 6
                    draw.ellipse([dx - 2, yp + day_size + 3, dx + 2, yp + day_size + 7], fill=dot_col)
        
        yp += cell_h
    
    return glass_bg


# ============================================================================
# WIDGET RENDERERS
# ============================================================================

def render_calendar_widget(base_image: Image.Image, tasks: List[Dict],
                           x: int, y: int, width: int, height: int,
                           settings: dict, scale: dict) -> Tuple[Image.Image, tuple]:
    """Render calendar with glassmorphism and DPI-aware sizing."""
    region = (x, y, x + width, y + height)
    
    glass_params = get_optimal_glass_params(base_image, region)
    colors = get_adaptive_text_colors(base_image, region)
    
    glass_bg = apply_glassmorphism(base_image, region, 
                                    border_radius=scale['border_radius'],
                                    **glass_params)
    
    style = settings.get('calendar_style', 'aesthetic')
    
    if style == 'compact' or style == 'minimal':
        result = render_calendar_compact(glass_bg, tasks, width, height, colors, scale)
    else:
        result = render_calendar_full(glass_bg, tasks, width, height, colors, scale, style)
    
    return result, (x, y)


def render_todo_widget(base_image: Image.Image, tasks: List[Dict],
                       x: int, y: int, width: int, height: int,
                       settings: dict, scale: dict) -> Tuple[Image.Image, tuple]:
    """Render To-Do with glassmorphism."""
    region = (x, y, x + width, y + height)
    
    glass_params = get_optimal_glass_params(base_image, region)
    colors = get_adaptive_text_colors(base_image, region)
    
    glass_bg = apply_glassmorphism(base_image, region,
                                    border_radius=scale['border_radius'],
                                    **glass_params)
    
    draw = ImageDraw.Draw(glass_bg)
    
    text_color = (*colors['text'], 255)
    text_secondary = (*colors['text_secondary'], 255)
    
    padding = scale['padding']
    yp = padding
    
    # Header
    header_size = calculate_font_size(width, height, 'header', scale['dpi_scale'])
    header_font = get_font(header_size, bold=True)
    draw_text_shadow(draw, (padding, yp), "To Do", header_font, text_color, colors['shadow'])
    yp += int(header_size * 1.8)
    
    # Divider
    draw.line([(padding, yp), (width - padding, yp)], fill=(*text_secondary[:3], 60), width=1)
    yp += 8
    
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
    
    body_size = calculate_font_size(width, height, 'body', scale['dpi_scale'])
    task_font = get_font(body_size, bold=False)
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
        
        draw.text((padding + 30, yp - 1), title, font=task_font, fill=text_color)
        yp += line_h
    
    if not upcoming:
        draw.text((padding, yp), "No tasks", font=task_font, fill=text_secondary)
    
    return glass_bg, (x, y)


def render_notes_widget(base_image: Image.Image,
                        x: int, y: int, width: int, height: int,
                        settings: dict, scale: dict) -> Tuple[Image.Image, tuple]:
    """Render Notes with glassmorphism."""
    region = (x, y, x + width, y + height)
    notes_text = load_notes()
    
    glass_params = get_optimal_glass_params(base_image, region)
    colors = get_adaptive_text_colors(base_image, region)
    
    glass_bg = apply_glassmorphism(base_image, region,
                                    border_radius=scale['border_radius'],
                                    **glass_params)
    
    draw = ImageDraw.Draw(glass_bg)
    
    text_color = (*colors['text'], 255)
    text_secondary = (*colors['text_secondary'], 255)
    
    padding = scale['padding']
    yp = padding
    
    header_size = calculate_font_size(width, height, 'header', scale['dpi_scale'])
    header_font = get_font(header_size, bold=True)
    draw_text_shadow(draw, (padding, yp), "Notes", header_font, text_color, colors['shadow'])
    yp += int(header_size * 1.8)
    
    draw.line([(padding, yp), (width - padding, yp)], fill=(*text_secondary[:3], 60), width=1)
    yp += 10
    
    body_size = calculate_font_size(width, height, 'body', scale['dpi_scale'])
    notes_font = get_font(body_size, bold=False)
    
    if notes_text:
        lines = []
        max_w = width - padding * 2
        
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
        
        line_h = int(body_size * 1.35)
        max_lines = (height - yp - padding) // line_h
        
        for line in lines[:max_lines]:
            draw.text((padding, yp), line, font=notes_font, fill=text_color)
            yp += line_h
    else:
        draw.text((padding, yp), "Add notes...", font=notes_font, fill=text_secondary)
    
    return glass_bg, (x, y)


def render_clock_widget(base_image: Image.Image,
                        x: int, y: int, width: int, height: int,
                        settings: dict, scale: dict) -> Tuple[Image.Image, tuple]:
    """Render Clock with glassmorphism."""
    region = (x, y, x + width, y + height)
    
    glass_params = get_optimal_glass_params(base_image, region)
    colors = get_adaptive_text_colors(base_image, region)
    
    glass_bg = apply_glassmorphism(base_image, region,
                                    border_radius=scale['border_radius'],
                                    **glass_params)
    
    draw = ImageDraw.Draw(glass_bg)
    text_color = (*colors['text'], 255)
    
    time_str = datetime.now().strftime("%H:%M")
    time_size = calculate_font_size(width, height, 'large_date', scale['dpi_scale']) 
    time_font = get_font(time_size, bold=True)
    
    draw_text_shadow(draw, (width // 2, height // 2), time_str, time_font, 
                     text_color, colors['shadow'], offset=3, anchor="mm")
    
    return glass_bg, (x, y)


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
    x = max(padding, min(x, base_w - w_w - padding))
    y = max(padding, min(y, base_h - w_h - padding))
    
    return (x, y)


def generate_wallpaper(base_image_path: str, tasks: List[Dict],
                       settings: dict = None) -> Optional[str]:
    """
    Generate wallpaper with smart-blending, DPI-aware widgets.
    """
    if settings is None:
        settings = load_settings()
    
    try:
        base_img = Image.open(base_image_path).convert('RGBA')
        base_w, base_h = base_img.size
        
        # Calculate DPI scale for this image
        scale = calculate_dpi_scale(base_w, base_h)
        
        result = base_img.copy()
        
        # Calendar
        if settings.get("calendar_enabled", True):
            size_pct = settings.get("calendar_size_percent", 25)
            cal_w, cal_h = calculate_widget_size(base_w, base_h, 'calendar', size_pct)
            
            x_pct = settings.get("calendar_x_percent", 0)
            y_pct = settings.get("calendar_y_percent", 0)
            x, y = get_widget_position((base_w, base_h), (cal_w, cal_h), x_pct, y_pct)
            
            widget, pos = render_calendar_widget(result, tasks, x, y, cal_w, cal_h, settings, scale)
            result.paste(widget, pos, widget)
        
        # To-Do
        if settings.get("todo_enabled", True):
            size_pct = settings.get("todo_width_percent", 22)
            todo_w, todo_h = calculate_widget_size(base_w, base_h, 'todo', size_pct)
            
            x_pct = settings.get("todo_x_percent", 0)
            y_pct = settings.get("todo_y_percent", 55)
            x, y = get_widget_position((base_w, base_h), (todo_w, todo_h), x_pct, y_pct)
            
            widget, pos = render_todo_widget(result, tasks, x, y, todo_w, todo_h, settings, scale)
            result.paste(widget, pos, widget)
        
        # Notes
        if settings.get("notes_enabled", True):
            size_pct = settings.get("notes_width_percent", 22)
            notes_w, notes_h = calculate_widget_size(base_w, base_h, 'notes', size_pct)
            
            x_pct = settings.get("notes_x_percent", 75)
            y_pct = settings.get("notes_y_percent", 60)
            x, y = get_widget_position((base_w, base_h), (notes_w, notes_h), x_pct, y_pct)
            
            widget, pos = render_notes_widget(result, x, y, notes_w, notes_h, settings, scale)
            result.paste(widget, pos, widget)
        
        # Clock
        if settings.get("clock_enabled", False):
            size_pct = settings.get("clock_size_percent", 15)
            clock_w, clock_h = calculate_widget_size(base_w, base_h, 'clock', size_pct)
            
            x_pct = settings.get("clock_x_percent", 80)
            y_pct = settings.get("clock_y_percent", 5)
            x, y = get_widget_position((base_w, base_h), (clock_w, clock_h), x_pct, y_pct)
            
            widget, pos = render_clock_widget(result, x, y, clock_w, clock_h, settings, scale)
            result.paste(widget, pos, widget)
        
        # Save
        output_path = OUTPUT_DIR / WALLPAPER_CONFIG["output_filename"]
        result.save(output_path, "PNG", quality=WALLPAPER_CONFIG["quality"])
        
        return str(output_path)
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None
