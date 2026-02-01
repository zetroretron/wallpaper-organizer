# 📅 Wallpaper Organizer

A beautiful desktop wallpaper organizer that overlays customizable widgets (Calendar, To-Do List, Notes, Clock) onto your wallpapers - inspired by aesthetic Canva desktop organizers.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ Features

- **Multi-Widget System** - Calendar, To-Do List, Notes, and Clock widgets
- **Live Preview** - See widget positions update in real-time as you adjust sliders
- **6 Beautiful Themes** - Dark, Light, Aesthetic, Minimal, Glass, Neon
- **Customizable Positions** - Place each widget anywhere on your wallpaper
- **Task Management** - Add tasks with categories (deadline, important, birthday, reminder)
- **Notes Widget** - Add custom notes that appear on your wallpaper
- **Recursive Image Scanning** - Finds wallpapers in subfolders automatically

## 📸 Preview

The app generates wallpapers like aesthetic desktop organizers with:
- Large date calendar display
- Upcoming tasks list
- Personal notes
- Optional clock widget

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/wallpaper-organizer.git
cd wallpaper-organizer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the app:
```bash
python main.py
```

## 📋 Requirements

- Python 3.10+
- Windows OS (for wallpaper setting)
- Pillow
- customtkinter
- tkcalendar

## 🎨 Themes

| Theme | Description |
|-------|-------------|
| Dark | Deep blue-gray with white text |
| Light | Cream/beige with brown accents |
| Aesthetic | Warm taupe tones |
| Minimal | Pure black with red accents |
| Glass | Glassmorphism with blur effect |
| Neon | Cyberpunk cyan and magenta |

## 📁 Project Structure

```
wallpaper-organizer/
├── main.py              # Entry point
├── config.py            # Settings and themes
├── storage.py           # Task/notes storage
├── wallpaper_generator.py  # Widget rendering
├── wallpaper_setter.py  # Windows API integration
├── gui/
│   ├── app.py          # Main GUI with live preview
│   └── components.py   # UI components
├── data/               # Tasks and settings storage
├── images/             # Your wallpaper images
└── output/             # Generated wallpapers
```

## 🔧 Usage

1. **Add Wallpapers** - Put images in the `images/` folder (subfolders supported)
2. **Select Image** - Click on a wallpaper in the Wallpapers tab
3. **Customize Widgets** - Go to Widgets tab, adjust positions with live preview
4. **Add Tasks** - Use the sidebar to add tasks with dates
5. **Add Notes** - Write notes in the sidebar
6. **Apply** - Click "Apply Wallpaper" to set as desktop background

## 📝 License

MIT License - feel free to use and modify!

## 🙏 Credits

Built with:
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - Modern UI
- [Pillow](https://pillow.readthedocs.io/) - Image processing
