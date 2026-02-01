"""
Wallpaper Generator - Premium Edition
Features: 4x Supersampled Text, Glassmorphism/Solid modes, Resolution-Independent Scaling
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
# RESOLUTION-INDEPENDENT TEXT SYSTEM
# ============================================================================

SUPERSAMPLE_SCALE = 4  # 4x for smooth antialiasing


def get_dynamic_font_size(widget_height: int, scale_factor: float = 0.05) -> int:
    """
    Calculate font size as percentage of widget container height.
    
    Args:
        widget_height: Height of the widget in pixels
        scale_factor: 0.0 to 1.0 (e.g., 0.05 = 5% of widget height)
    
    Returns:
        Font size in pixels, minimum 10px
    
    Example:
        widget_height=400, scale_factor=0.05 -> 20px font
        widget_height=800, scale_factor=0.05 -> 40px font (4K scaling!)
    """
    size = int(widget_height * scale_factor)
    return max(10, size)  # Minimum 10px for readability


def get_auto_contrast_color(background_image: Image.Image) -> Tuple[tuple, tuple, tuple]:
    """
    Analyze background luminance and return optimal text colors.
    
    Args:
        background_image: The cropped region behind the widget (PIL Image)
    
    Returns:
        (primary_text, secondary_text, shadow_color)
        - If bright background -> dark text
        - If dark background -> light text
    """
    # Convert to grayscale and calculate average luminance
    gray = background_image.convert('L')
    avg_luminance = np.mean(np.array(gray))
    
    # Threshold at 128 (middle of 0-255 range)
    if avg_luminance > 140:
        # BRIGHT background -> use DARK text
        primary = (25, 25, 30, 255)
        secondary = (60, 60, 70, 255)
        shadow = (255, 255, 255, 80)  # Light shadow for dark text
    elif avg_luminance > 90:
        # MID-TONE background -> use WHITE with strong shadow
        primary = (255, 255, 255, 255)
        secondary = (220, 220, 230, 255)
        shadow = (0, 0, 0, 180)  # Strong shadow for readability
    else:
        # DARK background -> use WHITE text
        primary = (255, 255, 255, 255)
        secondary = (200, 200, 210, 255)
        shadow = (0, 0, 0, 120)
    
    return primary, secondary, shadow


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
    # Ensure minimum size
    font_size = max(10, font_size)
    
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
    
    # Draw position
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
    
    # Downsample with LANCZOS
    final_w = max(1, text_w // SUPERSAMPLE_SCALE)
    final_h = max(1, text_h // SUPERSAMPLE_SCALE)
    
    result = large_img.resize((final_w + 5, final_h + 5), Image.Resampling.LANCZOS)
    return result


def draw_text(target: Image.Image, pos: tuple, text: str,
              widget_height: int, scale_factor: float, colors: tuple,
              bold: bool = True, anchor: str = None):
    """
    All-in-one text drawing with dynamic sizing and auto-contrast.
    
    Args:
        target: Image to draw on
        pos: (x, y) position
        text: Text string
        widget_height: Height of widget container (for font scaling)
        scale_factor: Font size as % of widget height (0.05 = 5%)
        colors: (primary, secondary, shadow) tuple from get_auto_contrast_color
        bold: Whether to use bold font
        anchor: 'mt' (middle-top) or 'mm' (middle-middle) or None (left-top)
    """
    primary, secondary, shadow = colors
    font_size = get_dynamic_font_size(widget_height, scale_factor)
    
    text_img = render_smooth_text(text, font_size, primary, bold, shadow)
    
    x, y = pos
    w, h = text_img.size
    
    if anchor == 'mt':
        x = x - w // 2
    elif anchor == 'mm':
        x = x - w // 2
        y = y - h // 2
    
    target.paste(text_img, (int(x), int(y)), text_img)
    return font_size  # Return actual size for layout calculations



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
    """
    Calculate font size as percentage of widget height.
    This ensures text scales properly from 1080p to 4K.
    
    Font roles and their target height percentages:
    - large_date: 35% of widget height (big date display)
    - title: 8% of widget height
    - header: 7% of widget height
    - body: 5.5% of widget height
    - weekday: 5% of widget height
    - day: 5.5% of widget height
    - small: 4% of widget height
    """
    # Percentage of widget height for each font role
    height_percentages = {
        'large_date': 0.30,  # 30% of widget height
        'title': 0.075,      # 7.5%
        'header': 0.065,     # 6.5%
        'body': 0.055,       # 5.5%
        'weekday': 0.05,     # 5%
        'day': 0.055,        # 5.5%
        'small': 0.04,       # 4%
    }
    
    pct = height_percentages.get(font_role, 0.05)
    
    # Calculate size from widget height
    size = int(widget_height * pct)
    
    # Apply DPI scale for extra sharpness on high-res
    size = int(size * (0.8 + dpi_scale * 0.2))
    
    # Minimum readable sizes (safety floor)
    min_sizes = {
        'large_date': 24,
        'title': 12,
        'header': 11,
        'body': 10,
        'weekday': 9,
        'day': 10,
        'small': 9,
    }
    
    # No maximum - let it scale freely for 4K/8K
    return max(min_sizes.get(font_role, 9), size)



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


def get_adaptive_colors(image: Image.Image, region: tuple) -> dict:
    """
    Get optimal text colors based on ACTUAL background luminance.
    This is the critical fix for contrast issues.
    """
    cropped = image.crop(region)
    
    # Use the new auto-contrast function
    primary, secondary, shadow = get_auto_contrast_color(cropped)
    
    # Generate accent colors from dominant color
    import colorsys
    color_crop = cropped.convert('RGB').resize((30, 30))
    dominant = tuple(map(int, np.mean(np.array(color_crop).reshape(-1, 3), axis=0)))
    
    r, g, b = [x / 255.0 for x in dominant]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    
    h_accent = (h + 0.45) % 1.0
    s_accent = min(1.0, s * 1.5 + 0.3)
    r, g, b = colorsys.hls_to_rgb(h_accent, 0.55, s_accent)
    accent = (int(r * 255), int(g * 255), int(b * 255), 255)
    
    h_today = (h + 0.3) % 1.0
    r, g, b = colorsys.hls_to_rgb(h_today, 0.5, 0.8)
    today = (int(r * 255), int(g * 255), int(b * 255), 255)
    
    # Calculate luminance for reference
    gray = cropped.convert('L')
    avg_luminance = np.mean(np.array(gray))
    
    return {
        'text': primary, 
        'text_secondary': secondary, 
        'shadow': shadow,
        'accent': accent, 
        'today': today, 
        'luminance': avg_luminance
    }



# ============================================================================
# WIDGET RENDERERS - Resolution Independent
# ============================================================================

def render_calendar_widget(base_image: Image.Image, tasks: List[Dict],
                           x: int, y: int, width: int, height: int,
                           settings: dict, scale: dict, theme: dict) -> Tuple[Image.Image, tuple]:
    """
    Render calendar with resolution-independent text.
    Font sizes are percentages of widget height.
    """
    region = (x, y, x + width, y + height)
    use_glass = settings.get('blend_mode', 'glass') == 'glass'
    
    # Create widget background
    if use_glass:
        glass_params = get_optimal_glass_params(base_image, region)
        widget = apply_glassmorphism(base_image, region, border_radius=scale['border_radius'],
                                      **glass_params)
    else:
        widget = apply_solid_background(width, height, theme, 
                                         opacity=int(settings.get('calendar_opacity', 90) * 255 / 100),
                                         border_radius=scale['border_radius'])
    
    # Get AUTO-CONTRAST colors from actual background
    colors = get_adaptive_colors(base_image, region)
    
    # For solid mode with light themes, override with theme colors
    if not use_glass:
        # Check if theme is light-colored
        theme_brightness = sum(theme['bg_color']) / 3
        if theme_brightness > 180:
            colors['text'] = (*theme['text_color'], 255)
            colors['text_secondary'] = (*theme['text_secondary'], 255)
            colors['today'] = (*theme['today_color'], 255)
            colors['shadow'] = None
    
    text_color = colors['text']
    text_secondary = colors['text_secondary']
    accent = colors['accent']
    today_color = colors['today']
    shadow = colors['shadow']
    
    padding = int(height * 0.04)  # 4% padding
    yp = padding
    today_dt = datetime.now()
    style = settings.get('calendar_style', 'aesthetic')
    
    draw = ImageDraw.Draw(widget)
    
    # === LARGE DATE (aesthetic mode) ===
    if style not in ['compact', 'minimal']:
        # Large date = 25% of widget height
        large_font = get_dynamic_font_size(height, 0.25)
        day_str = f"{today_dt.day:02d}"
        
        text_img = render_smooth_text(day_str, large_font, text_color, bold=True, shadow_color=shadow)
        widget.paste(text_img, (padding + 5, yp), text_img)
        
        # Month/year next to large date (7% and 6%)
        month_font = get_dynamic_font_size(height, 0.07)
        year_font = get_dynamic_font_size(height, 0.06)
        mx = padding + int(large_font * 1.4)
        
        month_img = render_smooth_text(calendar.month_name[today_dt.month], month_font, text_secondary, bold=False)
        widget.paste(month_img, (mx, yp + 5), month_img)
        
        year_img = render_smooth_text(str(today_dt.year), year_font, text_secondary, bold=False)
        widget.paste(year_img, (mx, yp + month_font + 10), year_img)
        
        yp += int(large_font * 1.15)
    else:
        # Compact header (6% of height)
        header_font = get_dynamic_font_size(height, 0.06)
        header_text = f"{calendar.month_abbr[today_dt.month]} {today_dt.day}, {today_dt.year}"
        
        text_img = render_smooth_text(header_text, header_font, text_color, bold=True, shadow_color=shadow)
        widget.paste(text_img, (padding, yp), text_img)
        yp += int(header_font * 1.8)
    
    # === DIVIDER ===
    draw.line([(padding, yp), (width - padding, yp)], fill=(*text_secondary[:3], 60), width=1)
    yp += int(height * 0.025)
    
    # === WEEKDAYS (4.5% of height) ===
    cell_w = (width - padding * 2) // 7
    wd_font = get_dynamic_font_size(height, 0.045)
    weekdays = ["S", "M", "T", "W", "T", "F", "S"]
    
    for i, wd in enumerate(weekdays):
        wx = padding + i * cell_w + cell_w // 2
        col = accent if i == 0 else text_secondary
        text_img = render_smooth_text(wd, wd_font, col, bold=True)
        widget.paste(text_img, (wx - text_img.width // 2, yp), text_img)
    
    yp += int(wd_font * 1.6)
    
    # === CALENDAR GRID (5% of height per day) ===
    cal_obj = calendar.Calendar(firstweekday=6)
    month_days = cal_obj.monthdayscalendar(today_dt.year, today_dt.month)
    
    tasks_by_date = {}
    for t in tasks:
        d = t.get("date", "")
        if d not in tasks_by_date:
            tasks_by_date[d] = []
        tasks_by_date[d].append(t)
    
    day_font = get_dynamic_font_size(height, 0.05)
    cell_h = int(height * 0.08)
    max_weeks = 5 if style in ['compact', 'minimal'] else 6
    
    for week in month_days[:max_weeks]:
        for i, day in enumerate(week):
            if day == 0:
                continue
            
            cx = padding + i * cell_w + cell_w // 2
            date_str = f"{today_dt.year}-{today_dt.month:02d}-{day:02d}"
            has_tasks = date_str in tasks_by_date
            
            # Today highlight
            if day == today_dt.day:
                r = int(day_font * 0.8)
                draw.ellipse([cx - r, yp - r + 4, cx + r, yp + r + 4], fill=today_color)
                day_text_col = (255, 255, 255, 255)
            elif i == 0:
                day_text_col = accent
            else:
                day_text_col = text_color
            
            text_img = render_smooth_text(str(day), day_font, day_text_col, bold=False)
            widget.paste(text_img, (cx - text_img.width // 2, yp + 4), text_img)
            
            # Task dots
            if has_tasks and day != today_dt.day:
                for j, task in enumerate(tasks_by_date[date_str][:2]):
                    cat = task.get("category", "default")
                    dot_col = (*CATEGORY_COLORS.get(cat, (150, 150, 150)), 255)
                    dx = cx - 3 + j * 6
                    draw.ellipse([dx - 2, yp + day_font + 3, dx + 2, yp + day_font + 7], fill=dot_col)
        
        yp += cell_h
    
    return widget, (x, y)


def render_todo_widget(base_image: Image.Image, tasks: List[Dict],
                       x: int, y: int, width: int, height: int,
                       settings: dict, scale: dict, theme: dict) -> Tuple[Image.Image, tuple]:
    """Render To-Do with resolution-independent text."""
    region = (x, y, x + width, y + height)
    use_glass = settings.get('blend_mode', 'glass') == 'glass'
    
    if use_glass:
        glass_params = get_optimal_glass_params(base_image, region)
        widget = apply_glassmorphism(base_image, region, border_radius=scale['border_radius'],
                                      **glass_params)
    else:
        widget = apply_solid_background(width, height, theme,
                                         opacity=int(settings.get('todo_opacity', 85) * 255 / 100),
                                         border_radius=scale['border_radius'])
    
    # Auto-contrast colors from actual background
    colors = get_adaptive_colors(base_image, region)
    text_color = colors['text']
    text_secondary = colors['text_secondary']
    shadow = colors['shadow']
    
    draw = ImageDraw.Draw(widget)
    padding = int(height * 0.05)
    yp = padding
    
    # Header (7% of height)
    header_font = get_dynamic_font_size(height, 0.07)
    text_img = render_smooth_text("To Do", header_font, text_color, bold=True, shadow_color=shadow)
    widget.paste(text_img, (padding, yp), text_img)
    yp += int(header_font * 1.8)
    
    draw.line([(padding, yp), (width - padding, yp)], fill=(*text_secondary[:3], 60), width=1)
    yp += int(height * 0.025)
    
    # Tasks (5% font size)
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
    
    body_font = get_dynamic_font_size(height, 0.055)
    line_h = int(body_font * 1.6)
    max_tasks = (height - yp - padding) // line_h
    
    for delta, task in upcoming[:max_tasks]:
        if yp > height - padding - 10:
            break
        
        cat = task.get("category", "default")
        cat_color = (*CATEGORY_COLORS.get(cat, (150, 150, 150)), 255)
        dot_size = max(4, int(body_font * 0.3))
        draw.ellipse([padding, yp + 3, padding + dot_size * 2, yp + 3 + dot_size * 2], fill=cat_color)
        
        # Checkbox
        cb_size = max(8, int(body_font * 0.5))
        draw.rectangle([padding + dot_size * 2 + 6, yp + 2, 
                       padding + dot_size * 2 + 6 + cb_size, yp + 2 + cb_size],
                       outline=text_secondary, width=1)
        
        title = task.get("title", "")
        max_chars = int((width - padding * 2 - dot_size * 2 - cb_size - 20) / (body_font * 0.5))
        if len(title) > max_chars:
            title = title[:max_chars - 2] + ".."
        
        text_img = render_smooth_text(title, body_font, text_color, bold=False)
        widget.paste(text_img, (padding + dot_size * 2 + cb_size + 12, yp - 1), text_img)
        yp += line_h
    
    if not upcoming:
        text_img = render_smooth_text("No tasks", body_font, text_secondary, bold=False)
        widget.paste(text_img, (padding, yp), text_img)
    
    return widget, (x, y)


def render_notes_widget(base_image: Image.Image,
                        x: int, y: int, width: int, height: int,
                        settings: dict, scale: dict, theme: dict) -> Tuple[Image.Image, tuple]:
    """Render Notes with resolution-independent text."""
    region = (x, y, x + width, y + height)
    notes_text = load_notes()
    use_glass = settings.get('blend_mode', 'glass') == 'glass'
    
    if use_glass:
        glass_params = get_optimal_glass_params(base_image, region)
        widget = apply_glassmorphism(base_image, region, border_radius=scale['border_radius'],
                                      **glass_params)
    else:
        widget = apply_solid_background(width, height, theme,
                                         opacity=int(settings.get('notes_opacity', 85) * 255 / 100),
                                         border_radius=scale['border_radius'])
    
    # Auto-contrast colors
    colors = get_adaptive_colors(base_image, region)
    text_color = colors['text']
    text_secondary = colors['text_secondary']
    shadow = colors['shadow']
    
    draw = ImageDraw.Draw(widget)
    padding = int(height * 0.06)
    yp = padding
    
    # Header (7%)
    header_font = get_dynamic_font_size(height, 0.07)
    text_img = render_smooth_text("Notes", header_font, text_color, bold=True, shadow_color=shadow)
    widget.paste(text_img, (padding, yp), text_img)
    yp += int(header_font * 1.8)
    
    draw.line([(padding, yp), (width - padding, yp)], fill=(*text_secondary[:3], 60), width=1)
    yp += int(height * 0.03)
    
    # Body text (5%)
    body_font = get_dynamic_font_size(height, 0.05)
    
    if notes_text:
        font = get_font(body_font, bold=False)
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
        
        line_h = int(body_font * 1.4)
        max_lines = (height - yp - padding) // line_h
        
        for line in lines[:max_lines]:
            text_img = render_smooth_text(line, body_font, text_color, bold=False)
            widget.paste(text_img, (padding, yp), text_img)
            yp += line_h
    else:
        text_img = render_smooth_text("Add notes...", body_font, text_secondary, bold=False)
        widget.paste(text_img, (padding, yp), text_img)
    
    return widget, (x, y)


def render_clock_widget(base_image: Image.Image,
                        x: int, y: int, width: int, height: int,
                        settings: dict, scale: dict, theme: dict) -> Tuple[Image.Image, tuple]:
    """Render Clock with resolution-independent text."""
    region = (x, y, x + width, y + height)
    use_glass = settings.get('blend_mode', 'glass') == 'glass'
    
    if use_glass:
        glass_params = get_optimal_glass_params(base_image, region)
        widget = apply_glassmorphism(base_image, region, border_radius=scale['border_radius'],
                                      **glass_params)
    else:
        widget = apply_solid_background(width, height, theme,
                                         opacity=int(settings.get('clock_opacity', 90) * 255 / 100),
                                         border_radius=scale['border_radius'])
    
    # Auto-contrast colors
    colors = get_adaptive_colors(base_image, region)
    text_color = colors['text']
    shadow = colors['shadow']
    
    # Time text (50% of height for clock)
    time_str = datetime.now().strftime("%H:%M")
    time_font = get_dynamic_font_size(height, 0.50)
    
    text_img = render_smooth_text(time_str, time_font, text_color, bold=True, shadow_color=shadow)
    
    # Center the text
    tx = (width - text_img.width) // 2
    ty = (height - text_img.height) // 2
    widget.paste(text_img, (tx, ty), text_img)
    
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
