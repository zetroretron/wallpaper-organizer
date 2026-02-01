"""
Wallpaper Calendar App - Main Entry Point

A desktop application that overlays a calendar with tasks/important dates
onto your favorite wallpapers and sets them as your Windows desktop background.

Usage:
    python main.py
"""
import sys
from pathlib import Path

# Ensure we're in the right directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from gui.app import run_app


if __name__ == "__main__":
    run_app()
