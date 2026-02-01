"""
Configuration settings for Wallpaper Calendar App
Enhanced with multi-widget system
"""
import os
import json
from pathlib import Path

# Base paths
APP_DIR = Path(__file__).parent.absolute()
DATA_DIR = APP_DIR / "data"
IMAGES_DIR = APP_DIR / "images"
OUTPUT_DIR = APP_DIR / "output"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Data files
TASKS_FILE = DATA_DIR / "tasks.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
NOTES_FILE = DATA_DIR / "notes.json"

# Default widget settings
DEFAULT_SETTINGS = {
    # Global settings
    "theme": "dark",
    "blend_mode": "glass",  # "glass" (frosted) or "solid" (opaque)
    "font_scale": 100,  # 50-150% font size scaling
    
    # Calendar widget
    "calendar_enabled": True,
    "calendar_x_percent": 0,
    "calendar_y_percent": 0,
    "calendar_size_percent": 28,
    "calendar_opacity": 90,
    "calendar_style": "aesthetic",  # aesthetic, compact, minimal, classic
    
    # To-Do widget
    "todo_enabled": True,
    "todo_x_percent": 0,
    "todo_y_percent": 55,
    "todo_width_percent": 22,
    "todo_height_percent": 40,
    "todo_opacity": 85,
    
    # Notes widget
    "notes_enabled": True,
    "notes_x_percent": 75,
    "notes_y_percent": 60,
    "notes_width_percent": 22,
    "notes_height_percent": 35,
    "notes_opacity": 85,
    
    # Clock widget
    "clock_enabled": False,
    "clock_x_percent": 80,
    "clock_y_percent": 5,
    "clock_size_percent": 15,
}


# Theme definitions
THEMES = {
    "dark": {
        "name": "Dark",
        "bg_color": (25, 25, 35),
        "header_color": (45, 45, 60),
        "text_color": (255, 255, 255),
        "text_secondary": (180, 180, 190),
        "today_color": (100, 149, 237),
        "weekend_color": (150, 150, 160),
        "accent": (100, 149, 237),
        "border_color": (60, 60, 80),
    },
    "light": {
        "name": "Light",
        "bg_color": (252, 250, 248),
        "header_color": (240, 238, 235),
        "text_color": (50, 45, 40),
        "text_secondary": (120, 115, 110),
        "today_color": (180, 130, 100),
        "weekend_color": (150, 140, 130),
        "accent": (180, 130, 100),
        "border_color": (220, 215, 210),
    },
    "glass": {
        "name": "Glassmorphism",
        "bg_color": (255, 255, 255),
        "header_color": (255, 255, 255),
        "text_color": (255, 255, 255),
        "text_secondary": (220, 220, 220),
        "today_color": (255, 200, 150),
        "weekend_color": (200, 200, 200),
        "accent": (255, 200, 150),
        "border_color": (255, 255, 255),
        "blur": True,
    },
    "minimal": {
        "name": "Minimal",
        "bg_color": (15, 15, 20),
        "header_color": (15, 15, 20),
        "text_color": (255, 255, 255),
        "text_secondary": (140, 140, 145),
        "today_color": (255, 100, 100),
        "weekend_color": (120, 120, 125),
        "accent": (255, 100, 100),
        "border_color": (40, 40, 50),
    },
    "aesthetic": {
        "name": "Aesthetic",
        "bg_color": (215, 200, 190),
        "header_color": (200, 185, 175),
        "text_color": (70, 60, 55),
        "text_secondary": (120, 105, 95),
        "today_color": (160, 100, 80),
        "weekend_color": (140, 120, 110),
        "accent": (160, 100, 80),
        "border_color": (180, 165, 155),
    },
    "neon": {
        "name": "Neon",
        "bg_color": (10, 10, 20),
        "header_color": (20, 20, 40),
        "text_color": (0, 255, 255),
        "text_secondary": (100, 200, 200),
        "today_color": (255, 0, 200),
        "weekend_color": (150, 0, 200),
        "accent": (255, 0, 200),
        "border_color": (0, 255, 255),
    },
}

# Calendar styles
CALENDAR_STYLES = {
    "aesthetic": {
        "show_large_date": True,
        "rounded_corners": 20,
        "show_month_name": True,
        "weekday_format": "full",
    },
    "compact": {
        "show_large_date": False,
        "rounded_corners": 15,
        "show_month_name": True,
        "weekday_format": "single",
    },
    "minimal": {
        "show_large_date": False,
        "rounded_corners": 8,
        "show_month_name": True,
        "weekday_format": "single",
    },
    "classic": {
        "show_large_date": False,
        "rounded_corners": 12,
        "show_month_name": True,
        "weekday_format": "short",
    },
}

# Task category colors
CATEGORY_COLORS = {
    "deadline": (231, 76, 60),
    "important": (241, 196, 15),
    "birthday": (155, 89, 182),
    "reminder": (46, 204, 113),
    "default": (149, 165, 166),
}

# Supported image formats
SUPPORTED_FORMATS = ('.png', '.jpg', '.jpeg', '.bmp', '.webp')


def load_settings():
    """Load user settings from file"""
    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()
    
    try:
        with open(SETTINGS_FILE, 'r') as f:
            saved = json.load(f)
            settings = DEFAULT_SETTINGS.copy()
            settings.update(saved)
            return settings
    except:
        return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    """Save user settings to file"""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except:
        return False


def load_notes():
    """Load notes from file"""
    if not NOTES_FILE.exists():
        return ""
    try:
        with open(NOTES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("content", "")
    except:
        return ""


def save_notes(content):
    """Save notes to file"""
    try:
        with open(NOTES_FILE, 'w', encoding='utf-8') as f:
            json.dump({"content": content}, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False


def get_theme(theme_name):
    """Get theme colors by name"""
    return THEMES.get(theme_name, THEMES["dark"])


# Wallpaper settings
WALLPAPER_CONFIG = {
    "output_filename": "wallpaper_with_calendar.png",
    "quality": 95,
}
