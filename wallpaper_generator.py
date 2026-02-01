"""
Wallpaper Generator - Multi-Widget System
Creates aesthetic wallpapers with Calendar, To-Do, and Notes widgets
"""
from datetime import datetime, timedelta
import calendar
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from config import (
    THEMES, CATEGORY_COLORS, CALENDAR_STYLES, WALLPAPER_CONFIG, OUTPUT_DIR,
    load_settings, load_notes, get_theme
)


def get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """Get font with fallback"""
    font_names = [
        "Segoe UI Bold" if bold else "Segoe UI",
        "Arial Bold" if bold else "Arial",
        "Calibri Bold" if bold else "Calibri",
    ]
    
    for font_name in font_names:
        try:
            return ImageFont.truetype(font_name, size)
        except (OSError, IOError):
            continue
    
    return ImageFont.load_default()


def get_script_font(size: int) -> ImageFont.FreeTypeFont:
    """Get decorative/script font for headers"""
    font_names = ["Georgia", "Times New Roman", "Palatino Linotype", "Segoe UI"]
    
    for font_name in font_names:
        try:
            return ImageFont.truetype(font_name, size)
        except:
            continue
    
    return get_font(size, bold=True)


def analyze_region_brightness(image: Image.Image, region: Tuple[int, int, int, int]) -> float:
    """Analyze average brightness of image region"""
    try:
        x1, y1, x2, y2 = region
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(image.width, x2), min(image.height, y2)
        
        cropped = image.crop((x1, y1, x2, y2))
        gray = cropped.convert('L')
        pixels = list(gray.getdata())
        return sum(pixels) / len(pixels) if pixels else 128
    except:
        return 128


def draw_text_shadow(draw, pos, text, font, fill, shadow_color=(0,0,0,150), 
                     anchor="lt", offset=2):
    """Draw text with shadow for visibility"""
    x, y = pos
    # Draw shadow
    for dx, dy in [(-offset, -offset), (offset, -offset), (-offset, offset), (offset, offset),
                   (0, -offset), (0, offset), (-offset, 0), (offset, 0)]:
        draw.text((x + dx, y + dy), text, font=font, fill=shadow_color, anchor=anchor)
    # Draw main text
    draw.text(pos, text, font=font, fill=fill, anchor=anchor)


def render_calendar_widget(tasks: List[Dict], width: int, height: int, 
                           settings: dict, theme: dict) -> Image.Image:
    """
    Render aesthetic calendar widget inspired by the reference images
    """
    style = CALENDAR_STYLES.get(settings.get("calendar_style", "aesthetic"), CALENDAR_STYLES["aesthetic"])
    opacity = int(settings.get("calendar_opacity", 90) * 255 / 100)
    
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Colors with opacity
    bg_r, bg_g, bg_b = theme["bg_color"]
    bg_color = (bg_r, bg_g, bg_b, opacity)
    text_color = (*theme["text_color"], 255)
    text_secondary = (*theme["text_secondary"], 255)
    today_color = (*theme["today_color"], 255)
    weekend_color = (*theme["weekend_color"], 255)
    border_color = (*theme.get("border_color", theme["header_color"]), 100)
    
    # Draw background
    radius = style["rounded_corners"]
    padding = 15
    draw.rounded_rectangle(
        [padding, padding, width - padding, height - padding],
        radius=radius,
        fill=bg_color,
        outline=border_color,
        width=2
    )
    
    # Current date info
    today = datetime.now()
    current_year = today.year
    current_month = today.month
    current_day = today.day
    month_name = calendar.month_name[current_month]
    
    # Font sizes based on widget size
    base = max(width // 16, 12)
    
    y_offset = padding + 20
    
    # AESTHETIC STYLE: Large date number + month name
    if style["show_large_date"]:
        # Large day number
        large_font = get_font(int(base * 4), bold=True)
        day_str = f"{current_day:02d}"
        draw.text((padding + 25, y_offset), day_str, font=large_font, fill=text_color)
        
        # Month and year to the right
        month_font = get_script_font(int(base * 1.2))
        draw.text((padding + 25 + base * 5, y_offset + 10), month_name, 
                  font=month_font, fill=text_secondary)
        draw.text((padding + 25 + base * 5, y_offset + 10 + base * 1.5), str(current_year),
                  font=get_font(int(base * 1.0), bold=False), fill=text_secondary)
        
        y_offset += int(base * 4.5)
    else:
        # Simple header
        header_font = get_font(int(base * 1.4), bold=True)
        draw.text((width // 2, y_offset), f"{month_name} {current_year}",
                  font=header_font, fill=text_color, anchor="mt")
        y_offset += int(base * 2.2)
    
    # Divider line
    draw.line([(padding + 20, y_offset), (width - padding - 20, y_offset)],
              fill=border_color, width=1)
    y_offset += 15
    
    # Weekday headers
    if style["weekday_format"] == "full":
        weekdays = ["S", "M", "T", "W", "T", "F", "S"]
    elif style["weekday_format"] == "short":
        weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    else:
        weekdays = ["S", "M", "T", "W", "T", "F", "S"]
    
    cell_width = (width - padding * 4) // 7
    start_x = padding * 2
    
    weekday_font = get_font(int(base * 0.85), bold=True)
    for i, day in enumerate(weekdays):
        x = start_x + i * cell_width + cell_width // 2
        color = weekend_color if i in [0, 6] else text_secondary
        draw.text((x, y_offset), day, font=weekday_font, fill=color, anchor="mt")
    
    y_offset += int(base * 1.8)
    
    # Calendar grid (Sunday start like in the examples)
    cal = calendar.Calendar(firstweekday=6)  # Sunday first
    month_days = cal.monthdayscalendar(current_year, current_month)
    
    # Create tasks lookup
    tasks_by_date = {}
    for task in tasks:
        date_str = task.get("date", "")
        if date_str not in tasks_by_date:
            tasks_by_date[date_str] = []
        tasks_by_date[date_str].append(task)
    
    cell_height = int(base * 1.9)
    day_font = get_font(int(base * 1.0), bold=False)
    
    for week_idx, week in enumerate(month_days[:6]):
        y = y_offset + week_idx * cell_height
        
        for day_idx, day in enumerate(week):
            if day == 0:
                continue
            
            x = start_x + day_idx * cell_width + cell_width // 2
            date_str = f"{current_year}-{current_month:02d}-{day:02d}"
            day_tasks = tasks_by_date.get(date_str, [])
            
            # Today circle
            if day == current_day:
                r = int(base * 0.9)
                draw.ellipse([x - r, y - r + 5, x + r, y + r + 5], fill=today_color)
                day_text_color = (255, 255, 255, 255) if sum(theme["today_color"]) < 450 else (0, 0, 0, 255)
            elif day_idx in [0, 6]:
                day_text_color = today_color  # Sundays/Saturdays highlighted
            else:
                day_text_color = text_color
            
            draw.text((x, y + 5), str(day), font=day_font, fill=day_text_color, anchor="mt")
            
            # Task dots
            if day_tasks and day != current_day:
                dot_y = y + int(base * 1.2)
                for i, task in enumerate(day_tasks[:2]):
                    cat = task.get("category", "default")
                    dot_color = (*CATEGORY_COLORS.get(cat, CATEGORY_COLORS["default"]), 255)
                    dot_x = x - 4 + i * 8
                    draw.ellipse([dot_x - 2, dot_y - 2, dot_x + 2, dot_y + 2], fill=dot_color)
    
    return img


def render_todo_widget(tasks: List[Dict], width: int, height: int,
                       settings: dict, theme: dict) -> Image.Image:
    """Render To-Do List widget"""
    opacity = int(settings.get("todo_opacity", 85) * 255 / 100)
    
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    bg_r, bg_g, bg_b = theme["bg_color"]
    bg_color = (bg_r, bg_g, bg_b, opacity)
    text_color = (*theme["text_color"], 255)
    text_secondary = (*theme["text_secondary"], 255)
    border_color = (*theme.get("border_color", theme["header_color"]), 100)
    
    padding = 12
    draw.rounded_rectangle(
        [padding, padding, width - padding, height - padding],
        radius=15,
        fill=bg_color,
        outline=border_color,
        width=2
    )
    
    # Header
    base = max(width // 14, 11)
    header_font = get_font(int(base * 1.2), bold=True)
    y = padding + 18
    
    draw.text((padding + 20, y), "To Do List", font=header_font, fill=text_color)
    y += int(base * 2.2)
    
    # Divider
    draw.line([(padding + 15, y), (width - padding - 15, y)], fill=border_color, width=1)
    y += 12
    
    # Tasks (upcoming 7 days)
    today = datetime.now().date()
    upcoming = []
    for task in tasks:
        try:
            task_date = datetime.strptime(task["date"], "%Y-%m-%d").date()
            delta = (task_date - today).days
            if -1 <= delta <= 7:  # Include today and next 7 days
                upcoming.append((delta, task))
        except:
            continue
    
    upcoming.sort(key=lambda x: (x[0], x[1].get("title", "")))
    
    task_font = get_font(int(base * 0.9), bold=False)
    small_font = get_font(int(base * 0.7), bold=False)
    line_height = int(base * 1.6)
    max_tasks = (height - y - padding - 20) // line_height
    
    for i, (delta, task) in enumerate(upcoming[:max_tasks]):
        if y > height - padding - 20:
            break
        
        # Category dot
        cat = task.get("category", "default")
        cat_color = (*CATEGORY_COLORS.get(cat, CATEGORY_COLORS["default"]), 255)
        draw.ellipse([padding + 20, y + 5, padding + 28, y + 13], fill=cat_color)
        
        # Checkbox (empty square)
        draw.rectangle([padding + 35, y + 3, padding + 47, y + 15], 
                      outline=text_secondary, width=1)
        
        # Task text
        title = task.get("title", "")
        max_chars = (width - padding * 2 - 60) // int(base * 0.5)
        if len(title) > max_chars:
            title = title[:max_chars - 2] + ".."
        
        draw.text((padding + 55, y), title, font=task_font, fill=text_color)
        
        y += line_height
    
    if not upcoming:
        draw.text((padding + 20, y), "No tasks", font=task_font, fill=text_secondary)
    
    return img


def render_notes_widget(width: int, height: int, settings: dict, theme: dict) -> Image.Image:
    """Render Notes widget"""
    opacity = int(settings.get("notes_opacity", 85) * 255 / 100)
    notes_text = load_notes()
    
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    bg_r, bg_g, bg_b = theme["bg_color"]
    bg_color = (bg_r, bg_g, bg_b, opacity)
    text_color = (*theme["text_color"], 255)
    text_secondary = (*theme["text_secondary"], 255)
    border_color = (*theme.get("border_color", theme["header_color"]), 100)
    
    padding = 12
    draw.rounded_rectangle(
        [padding, padding, width - padding, height - padding],
        radius=15,
        fill=bg_color,
        outline=border_color,
        width=2
    )
    
    # Header
    base = max(width // 14, 11)
    header_font = get_font(int(base * 1.2), bold=True)
    y = padding + 18
    
    draw.text((padding + 20, y), "Notes", font=header_font, fill=text_color)
    y += int(base * 2.2)
    
    # Divider
    draw.line([(padding + 15, y), (width - padding - 15, y)], fill=border_color, width=1)
    y += 15
    
    # Notes content
    if notes_text:
        notes_font = get_font(int(base * 0.85), bold=False)
        # Word wrap
        lines = []
        max_width = width - padding * 2 - 30
        
        for paragraph in notes_text.split('\n'):
            words = paragraph.split()
            current_line = ""
            for word in words:
                test_line = current_line + " " + word if current_line else word
                bbox = draw.textbbox((0, 0), test_line, font=notes_font)
                if bbox[2] - bbox[0] <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            if not paragraph:
                lines.append("")
        
        line_height = int(base * 1.4)
        max_lines = (height - y - padding - 10) // line_height
        
        for line in lines[:max_lines]:
            draw.text((padding + 20, y), line, font=notes_font, fill=text_color)
            y += line_height
    else:
        draw.text((padding + 20, y), "Add notes in the app...", 
                  font=get_font(int(base * 0.85), bold=False), fill=text_secondary)
    
    return img


def render_clock_widget(width: int, height: int, settings: dict, theme: dict) -> Image.Image:
    """Render Clock widget"""
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    bg_r, bg_g, bg_b = theme["bg_color"]
    opacity = 200
    bg_color = (bg_r, bg_g, bg_b, opacity)
    text_color = (*theme["text_color"], 255)
    border_color = (*theme.get("border_color", theme["header_color"]), 100)
    
    padding = 10
    draw.rounded_rectangle(
        [padding, padding, width - padding, height - padding],
        radius=15,
        fill=bg_color,
        outline=border_color,
        width=2
    )
    
    # Time
    now = datetime.now()
    time_str = now.strftime("%H:%M")
    
    base = max(width // 6, 20)
    time_font = get_font(int(base * 2), bold=True)
    
    draw.text((width // 2, height // 2), time_str, font=time_font, 
              fill=text_color, anchor="mm")
    
    return img


def get_widget_position(base_size: Tuple[int, int], widget_size: Tuple[int, int],
                        x_percent: int, y_percent: int) -> Tuple[int, int]:
    """Calculate widget position from percentages"""
    base_w, base_h = base_size
    w_w, w_h = widget_size
    
    # Position is the percentage of available space (not total)
    available_x = base_w - w_w
    available_y = base_h - w_h
    
    x = int(available_x * x_percent / 100)
    y = int(available_y * y_percent / 100)
    
    # Clamp to bounds with padding
    padding = 20
    x = max(padding, min(x, base_w - w_w - padding))
    y = max(padding, min(y, base_h - w_h - padding))
    
    return (x, y)


def generate_wallpaper(base_image_path: str, tasks: List[Dict], settings: dict = None) -> Optional[str]:
    """
    Generate wallpaper with multiple widgets
    """
    if settings is None:
        settings = load_settings()
    
    try:
        # Load base image
        base_img = Image.open(base_image_path).convert('RGBA')
        base_width, base_height = base_img.size
        theme = get_theme(settings.get("theme", "dark"))
        
        result = base_img.copy()
        
        # Calendar Widget
        if settings.get("calendar_enabled", True):
            size_pct = settings.get("calendar_size_percent", 28)
            cal_width = int(base_width * size_pct / 100)
            cal_height = int(cal_width * 1.1)
            
            # Limit size
            cal_width = max(250, min(cal_width, 500))
            cal_height = max(280, min(cal_height, 550))
            
            x_pct = settings.get("calendar_x_percent", 0)
            y_pct = settings.get("calendar_y_percent", 0)
            
            # Check if blur needed
            pos = get_widget_position((base_width, base_height), (cal_width, cal_height), x_pct, y_pct)
            if theme.get("blur"):
                region = result.crop((pos[0], pos[1], pos[0] + cal_width, pos[1] + cal_height))
                region = region.filter(ImageFilter.GaussianBlur(20))
                result.paste(region, pos)
            
            cal_widget = render_calendar_widget(tasks, cal_width, cal_height, settings, theme)
            result.paste(cal_widget, pos, cal_widget)
        
        # To-Do Widget
        if settings.get("todo_enabled", True):
            w_pct = settings.get("todo_width_percent", 22)
            h_pct = settings.get("todo_height_percent", 40)
            todo_width = int(base_width * w_pct / 100)
            todo_height = int(base_height * h_pct / 100)
            
            todo_width = max(180, min(todo_width, 400))
            todo_height = max(200, min(todo_height, 500))
            
            x_pct = settings.get("todo_x_percent", 0)
            y_pct = settings.get("todo_y_percent", 55)
            
            pos = get_widget_position((base_width, base_height), (todo_width, todo_height), x_pct, y_pct)
            if theme.get("blur"):
                region = result.crop((pos[0], pos[1], pos[0] + todo_width, pos[1] + todo_height))
                region = region.filter(ImageFilter.GaussianBlur(20))
                result.paste(region, pos)
            
            todo_widget = render_todo_widget(tasks, todo_width, todo_height, settings, theme)
            result.paste(todo_widget, pos, todo_widget)
        
        # Notes Widget
        if settings.get("notes_enabled", True):
            w_pct = settings.get("notes_width_percent", 22)
            h_pct = settings.get("notes_height_percent", 35)
            notes_width = int(base_width * w_pct / 100)
            notes_height = int(base_height * h_pct / 100)
            
            notes_width = max(180, min(notes_width, 400))
            notes_height = max(150, min(notes_height, 400))
            
            x_pct = settings.get("notes_x_percent", 75)
            y_pct = settings.get("notes_y_percent", 60)
            
            pos = get_widget_position((base_width, base_height), (notes_width, notes_height), x_pct, y_pct)
            if theme.get("blur"):
                region = result.crop((pos[0], pos[1], pos[0] + notes_width, pos[1] + notes_height))
                region = region.filter(ImageFilter.GaussianBlur(20))
                result.paste(region, pos)
            
            notes_widget = render_notes_widget(notes_width, notes_height, settings, theme)
            result.paste(notes_widget, pos, notes_widget)
        
        # Clock Widget
        if settings.get("clock_enabled", False):
            size_pct = settings.get("clock_size_percent", 15)
            clock_width = int(base_width * size_pct / 100)
            clock_height = int(clock_width * 0.5)
            
            x_pct = settings.get("clock_x_percent", 80)
            y_pct = settings.get("clock_y_percent", 5)
            
            pos = get_widget_position((base_width, base_height), (clock_width, clock_height), x_pct, y_pct)
            clock_widget = render_clock_widget(clock_width, clock_height, settings, theme)
            result.paste(clock_widget, pos, clock_widget)
        
        # Save
        output_path = OUTPUT_DIR / WALLPAPER_CONFIG["output_filename"]
        result.save(output_path, "PNG", quality=WALLPAPER_CONFIG["quality"])
        
        return str(output_path)
    
    except Exception as e:
        print(f"Error generating wallpaper: {e}")
        import traceback
        traceback.print_exc()
        return None
