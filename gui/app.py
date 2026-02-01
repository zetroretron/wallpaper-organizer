"""
Main Application GUI - Multi-Widget System with Live Preview
"""
import customtkinter as ctk
from datetime import datetime
from pathlib import Path
from typing import Optional
import sys
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    IMAGES_DIR, SUPPORTED_FORMATS, OUTPUT_DIR, THEMES, CALENDAR_STYLES,
    load_settings, save_settings, load_notes, save_notes
)
from storage import load_tasks, add_task, delete_task
from wallpaper_generator import generate_wallpaper
from wallpaper_setter import set_wallpaper
from gui.components import TaskCard, ImageThumbnail, CategorySelector

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class WallpaperCalendarApp(ctk.CTk):
    """Main Application Window with Live Preview"""
    
    def __init__(self):
        super().__init__()
        
        self.title("Wallpaper Organizer")
        self.geometry("1350x850")
        self.minsize(1150, 750)
        
        self.selected_image: Optional[str] = None
        self.image_thumbnails = []
        self.settings = load_settings()
        self._preview_pending = False
        self._preview_job = None
        
        self._create_layout()
        self._create_sidebar()
        self._create_main_content()
        
        self._refresh_tasks()
        self._refresh_images()
    
    def _create_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
    
    def _create_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=280, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nswe")
        sidebar.grid_propagate(False)
        
        sidebar_scroll = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        sidebar_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(sidebar_scroll, text="📅 Wallpaper\nOrganizer",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(15, 15))
        
        # Add Task
        task_frame = ctk.CTkFrame(sidebar_scroll, fg_color=("gray85", "gray20"))
        task_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(task_frame, text="➕ Add Task", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.task_title_entry = ctk.CTkEntry(task_frame, placeholder_text="Task title...", height=32)
        self.task_title_entry.pack(fill="x", padx=10, pady=3)
        
        date_frame = ctk.CTkFrame(task_frame, fg_color="transparent")
        date_frame.pack(fill="x", padx=10, pady=3)
        
        self.date_entry = ctk.CTkEntry(date_frame, placeholder_text="YYYY-MM-DD", width=100)
        self.date_entry.pack(side="left")
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        self.category_var = ctk.StringVar(value="deadline")
        ctk.CTkOptionMenu(date_frame, values=["deadline", "important", "birthday", "reminder"],
                          variable=self.category_var, width=100).pack(side="right")
        
        ctk.CTkButton(task_frame, text="Add Task", height=32, command=self._add_task).pack(fill="x", padx=10, pady=10)
        
        # Notes
        notes_frame = ctk.CTkFrame(sidebar_scroll, fg_color=("gray85", "gray20"))
        notes_frame.pack(fill="x", padx=5, pady=10)
        
        ctk.CTkLabel(notes_frame, text="📝 Notes", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.notes_textbox = ctk.CTkTextbox(notes_frame, height=80)
        self.notes_textbox.pack(fill="x", padx=10, pady=3)
        self.notes_textbox.insert("1.0", load_notes())
        
        ctk.CTkButton(notes_frame, text="Save Notes", height=28, fg_color="transparent", border_width=1,
                      command=self._save_notes).pack(fill="x", padx=10, pady=(3, 10))
        
        # Actions
        action_frame = ctk.CTkFrame(sidebar_scroll, fg_color="transparent")
        action_frame.pack(fill="x", padx=5, pady=10)
        
        ctk.CTkButton(action_frame, text="🖼 Apply Wallpaper", height=45,
                      fg_color=("#27AE60", "#1E8449"), hover_color=("#2ECC71", "#27AE60"),
                      command=self._apply_wallpaper).pack(fill="x", pady=3)
        
        ctk.CTkButton(action_frame, text="🔄 Refresh Images", height=32,
                      fg_color="transparent", border_width=1, command=self._refresh_images).pack(fill="x", pady=3)
        
        ctk.CTkButton(action_frame, text="📁 Open Images Folder", height=32,
                      fg_color="transparent", border_width=1, command=self._open_images_folder).pack(fill="x", pady=3)
        
        self.status_label = ctk.CTkLabel(sidebar, text="", font=ctk.CTkFont(size=10),
                                         text_color=("gray50", "gray60"), wraplength=260)
        self.status_label.pack(side="bottom", pady=10)
    
    def _create_main_content(self):
        main = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nswe", padx=15, pady=15)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(0, weight=1)
        
        self.tabview = ctk.CTkTabview(main, corner_radius=10)
        self.tabview.grid(row=0, column=0, sticky="nswe")
        
        self.tab_tasks = self.tabview.add("📋 Tasks")
        self.tab_wallpapers = self.tabview.add("🖼 Wallpapers")
        self.tab_widgets = self.tabview.add("🧩 Widgets")
        self.tab_preview = self.tabview.add("👁 Preview")
        
        self._create_tasks_tab()
        self._create_wallpapers_tab()
        self._create_widgets_tab()
        self._create_preview_tab()
    
    def _create_tasks_tab(self):
        self.tab_tasks.grid_columnconfigure(0, weight=1)
        self.tab_tasks.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(self.tab_tasks, text="Your Tasks", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        self.tasks_scroll = ctk.CTkScrollableFrame(self.tab_tasks, fg_color="transparent")
        self.tasks_scroll.grid(row=1, column=0, sticky="nswe")
        self.tasks_scroll.grid_columnconfigure(0, weight=1)
    
    def _create_wallpapers_tab(self):
        self.tab_wallpapers.grid_columnconfigure(0, weight=1)
        self.tab_wallpapers.grid_rowconfigure(1, weight=1)
        
        header = ctk.CTkFrame(self.tab_wallpapers, fg_color="transparent")
        header.grid(row=0, column=0, sticky="we", pady=(0, 10))
        
        ctk.CTkLabel(header, text="Select Wallpaper", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
        self.selected_label = ctk.CTkLabel(header, text="None selected", font=ctk.CTkFont(size=11), text_color=("gray50", "gray60"))
        self.selected_label.pack(side="right")
        
        self.gallery_scroll = ctk.CTkScrollableFrame(self.tab_wallpapers, fg_color="transparent")
        self.gallery_scroll.grid(row=1, column=0, sticky="nswe")
    
    def _create_widgets_tab(self):
        """Widget settings with LIVE PREVIEW"""
        # Main container with two columns: controls + preview
        self.tab_widgets.grid_columnconfigure(0, weight=2)
        self.tab_widgets.grid_columnconfigure(1, weight=3)
        self.tab_widgets.grid_rowconfigure(0, weight=1)
        
        # LEFT: Controls
        controls_frame = ctk.CTkScrollableFrame(self.tab_widgets, fg_color="transparent")
        controls_frame.grid(row=0, column=0, sticky="nswe", padx=(0, 10))
        
        # Theme selector
        theme_frame = ctk.CTkFrame(controls_frame)
        theme_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(theme_frame, text="🎨 Theme", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=10, pady=8)
        self.theme_var = ctk.StringVar(value=self.settings.get('theme', 'aesthetic'))
        theme_menu = ctk.CTkOptionMenu(theme_frame, values=list(THEMES.keys()), variable=self.theme_var,
                                        command=self._on_theme_change, width=120)
        theme_menu.pack(side="right", padx=10, pady=8)
        
        # Blend mode selector (Glass vs Solid)
        blend_frame = ctk.CTkFrame(controls_frame)
        blend_frame.pack(fill="x", pady=3)
        
        ctk.CTkLabel(blend_frame, text="🪟 Background", font=ctk.CTkFont(size=12)).pack(side="left", padx=10, pady=6)
        self.blend_var = ctk.StringVar(value=self.settings.get('blend_mode', 'glass'))
        blend_menu = ctk.CTkSegmentedButton(blend_frame, values=["glass", "solid"],
                                             variable=self.blend_var, command=self._on_blend_change)
        blend_menu.pack(side="right", padx=10, pady=6)


        # Calendar
        self._create_compact_widget_controls(controls_frame, "📅 Calendar", "calendar", show_size="calendar_size_percent")
        
        # Style for calendar
        style_frame = ctk.CTkFrame(controls_frame, fg_color=("gray85", "gray20"))
        style_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(style_frame, text="   Style:").pack(side="left", padx=5)
        self.cal_style_var = ctk.StringVar(value=self.settings.get('calendar_style', 'aesthetic'))
        ctk.CTkOptionMenu(style_frame, values=list(CALENDAR_STYLES.keys()),
                          variable=self.cal_style_var, command=self._on_cal_style_change, width=100).pack(side="right", padx=10, pady=5)
        
        # To-Do
        self._create_compact_widget_controls(controls_frame, "✅ To-Do", "todo", show_wh=True)
        
        # Notes
        self._create_compact_widget_controls(controls_frame, "📝 Notes", "notes", show_wh=True)
        
        # Clock
        self._create_compact_widget_controls(controls_frame, "🕐 Clock", "clock", show_size="clock_size_percent")
        
        # RIGHT: Live Preview
        preview_frame = ctk.CTkFrame(self.tab_widgets)
        preview_frame.grid(row=0, column=1, sticky="nswe")
        preview_frame.grid_columnconfigure(0, weight=1)
        preview_frame.grid_rowconfigure(1, weight=1)
        
        header = ctk.CTkFrame(preview_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="we", padx=10, pady=5)
        
        ctk.CTkLabel(header, text="🔴 Live Preview", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        
        ctk.CTkButton(header, text="↻ Refresh", width=80, height=28,
                      fg_color="transparent", border_width=1,
                      command=self._update_live_preview).pack(side="right")
        
        self.live_preview_label = ctk.CTkLabel(
            preview_frame,
            text="Select a wallpaper first\nthen adjust sliders to see live changes",
            font=ctk.CTkFont(size=12), text_color=("gray50", "gray60")
        )
        self.live_preview_label.grid(row=1, column=0, sticky="nswe", padx=10, pady=10)
    
    def _create_compact_widget_controls(self, parent, title, widget_key, show_size=None, show_wh=False):
        """Compact widget controls with live preview updates"""
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", pady=5)
        
        # Header row (Toggle checkbox)
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(8, 3))
        
        enabled_var = ctk.BooleanVar(value=self.settings.get(f"{widget_key}_enabled", True))
        setattr(self, f"{widget_key}_enabled_var", enabled_var)
        
        ctk.CTkCheckBox(header, text=title, font=ctk.CTkFont(size=12, weight="bold"),
                        variable=enabled_var,
                        command=lambda: self._on_widget_toggle(widget_key)).pack(side="left")
        
        # Controls Container
        controls = ctk.CTkFrame(frame, fg_color="transparent")
        controls.pack(fill="x", padx=5, pady=2)
        
        # 1. Position Controls (X, Y)
        self._add_control_row(controls, "Pos X %", f"{widget_key}_x_percent", 0, 100)
        self._add_control_row(controls, "Pos Y %", f"{widget_key}_y_percent", 0, 100)
        
        # 2. Size Controls (Width/Height or Size)
        if show_size:
            self._add_control_row(controls, "Size %", show_size, 10, 100)
        
        if show_wh:
            self._add_control_row(controls, "Width %", f"{widget_key}_width_percent", 10, 100)
            self._add_control_row(controls, "Height %", f"{widget_key}_height_percent", 10, 100)
            
        # 3. Appearance Controls (Opacity, Font)
        self._add_control_row(controls, "Opacity %", f"{widget_key}_opacity", 0, 100)
        self._add_control_row(controls, "Font %", f"{widget_key}_font_scale", 10, 300)

    def _on_pos_live(self, widget_key, axis, value):

        self.settings[f"{widget_key}_{axis}_percent"] = int(value)
        label = getattr(self, f"{widget_key}_{axis}_label")
        label.configure(text=f"{int(value)}%")
        save_settings(self.settings)
        self._schedule_preview_update()
    
    def _on_size_live(self, size_key, widget_key, value):
        self.settings[size_key] = int(value)
        label = getattr(self, f"{widget_key}_size_label")
        label.configure(text=f"{int(value)}%")
    
    def _add_control_row(self, parent, label_text, settings_key, min_val, max_val, callback_key=None):
        """Add a row with Label | Slider | Number Entry"""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=2)
        
        # Label
        ctk.CTkLabel(row, text=label_text, width=60, anchor="w").pack(side="left")
        
        # Current value
        current_val = self.settings.get(settings_key, min_val)
        
        # Variable to sync slider and entry
        var = ctk.IntVar(value=int(current_val))
        
        # Callback wrapper
        def on_change(value):
            val = int(float(value))
            self.settings[settings_key] = val
            save_settings(self.settings)
            self._schedule_preview_update()
        
        # Slider
        slider = ctk.CTkSlider(row, from_=min_val, to=max_val, variable=var, 
                               command=on_change, width=120)
        slider.pack(side="left", padx=5)
        
        # Entry (Number input)
        entry = ctk.CTkEntry(row, width=50, textvariable=var)
        entry.pack(side="left", padx=5)
        
        # Bind entry to update on Enter or FocusOut
        def on_entry_commit(event=None):
            try:
                val = int(entry.get())
                # Clamp value
                val = max(min_val, min(max_val, val))
                var.set(val)
                on_change(val)
            except ValueError:
                pass
                
        entry.bind("<Return>", on_entry_commit)
        entry.bind("<FocusOut>", on_entry_commit)

    
    def _on_widget_toggle(self, widget_key):
        var = getattr(self, f"{widget_key}_enabled_var")
        self.settings[f"{widget_key}_enabled"] = var.get()
        save_settings(self.settings)
        self._schedule_preview_update()
    
    def _on_theme_change(self, theme):
        self.settings['theme'] = theme
        save_settings(self.settings)
        self._schedule_preview_update()
    
    def _on_cal_style_change(self, style):
        self.settings['calendar_style'] = style
        save_settings(self.settings)
        self._schedule_preview_update()
    
    def _on_blend_change(self, mode):
        self.settings['blend_mode'] = mode
        save_settings(self.settings)
        self._schedule_preview_update()

    def _schedule_preview_update(self):
        """Debounce preview updates to avoid lag"""
        if self._preview_job:
            self.after_cancel(self._preview_job)
        self._preview_job = self.after(300, self._update_live_preview)
    
    def _update_live_preview(self):
        """Generate and show live preview"""
        if not self.selected_image:
            self.live_preview_label.configure(
                text="Select a wallpaper first\nin the Wallpapers tab",
                image=None
            )
            return
        
        from PIL import Image
        import tempfile
        
        try:
            # Save notes first
            content = self.notes_textbox.get("1.0", "end-1c")
            save_notes(content)
            
            tasks = load_tasks()
            self.settings = load_settings()
            
            # Generate preview
            temp_path = OUTPUT_DIR / "preview_temp.png"
            
            # Use the wallpaper generator
            output = generate_wallpaper(self.selected_image, tasks, self.settings)
            
            if output:
                img = Image.open(output)
                
                # Fit to preview area (max ~550x350)
                max_w, max_h = 550, 380
                ratio = min(max_w / img.width, max_h / img.height)
                size = (int(img.width * ratio), int(img.height * ratio))
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                self.live_preview_img = ctk.CTkImage(light_image=img, dark_image=img, size=size)
                self.live_preview_label.configure(image=self.live_preview_img, text="")
        except Exception as e:
            print(f"Live preview error: {e}")
            self.live_preview_label.configure(text=f"Preview error: {e}", image=None)
    
    def _create_preview_tab(self):
        self.tab_preview.grid_columnconfigure(0, weight=1)
        self.tab_preview.grid_rowconfigure(0, weight=1)
        
        self.preview_label = ctk.CTkLabel(
            self.tab_preview,
            text="Click 'Apply Wallpaper' to see the final result",
            font=ctk.CTkFont(size=14), text_color=("gray50", "gray60")
        )
        self.preview_label.grid(row=0, column=0)
    
    def _refresh_tasks(self):
        for widget in self.tasks_scroll.winfo_children():
            widget.destroy()
        
        tasks = load_tasks()
        
        if not tasks:
            ctk.CTkLabel(self.tasks_scroll, text="No tasks yet!", font=ctk.CTkFont(size=13),
                        text_color=("gray50", "gray60")).pack(pady=40)
            return
        
        tasks.sort(key=lambda t: t.get("date", "9999"))
        
        for task in tasks:
            card = TaskCard(self.tasks_scroll, task=task, on_delete=self._delete_task, on_edit=lambda t: None)
            card.pack(fill="x", pady=4)
    
    def _refresh_images(self):
        for widget in self.gallery_scroll.winfo_children():
            widget.destroy()
        self.image_thumbnails.clear()
        
        images = []
        if IMAGES_DIR.exists():
            for ext in SUPPORTED_FORMATS:
                images.extend(IMAGES_DIR.glob(f"*{ext}"))
                images.extend(IMAGES_DIR.glob(f"**/*{ext}"))
        
        images = list(set(images))
        
        if not images:
            ctk.CTkLabel(self.gallery_scroll, text=f"No images found.\nAdd to: {IMAGES_DIR}",
                        font=ctk.CTkFont(size=13), text_color=("gray50", "gray60")).pack(pady=40)
            return
        
        row_frame = None
        for i, img_path in enumerate(sorted(images)):
            if i % 5 == 0:
                row_frame = ctk.CTkFrame(self.gallery_scroll, fg_color="transparent")
                row_frame.pack(fill="x", pady=4)
            
            thumbnail = ImageThumbnail(row_frame, image_path=str(img_path),
                                        on_select=self._select_image,
                                        is_selected=(str(img_path) == self.selected_image))
            thumbnail.pack(side="left", padx=4)
            self.image_thumbnails.append(thumbnail)
        
        self._update_status(f"Found {len(images)} images")
    
    def _select_image(self, path):
        self.selected_image = path
        for t in self.image_thumbnails:
            t.set_selected(t.image_path == path)
        self.selected_label.configure(text=f"Selected: {Path(path).name}")
        
        # Trigger live preview if on widgets tab
        self._schedule_preview_update()
    
    def _add_task(self):
        title = self.task_title_entry.get().strip()
        date = self.date_entry.get().strip()
        category = self.category_var.get()
        
        if not title:
            self._update_status("⚠️ Enter task title")
            return
        
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except:
            self._update_status("⚠️ Invalid date")
            return
        
        add_task(title, date, category)
        self.task_title_entry.delete(0, "end")
        self.date_entry.delete(0, "end")
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self._refresh_tasks()
        self._update_status(f"✅ Added: {title}")
    
    def _delete_task(self, task_id):
        delete_task(task_id)
        self._refresh_tasks()
        self._update_status("🗑 Deleted")
    
    def _save_notes(self):
        content = self.notes_textbox.get("1.0", "end-1c")
        save_notes(content)
        self._update_status("📝 Notes saved")
    
    def _apply_wallpaper(self):
        if not self.selected_image:
            self._update_status("⚠️ Select image first")
            return
        
        self._update_status("⏳ Generating...")
        self.update()
        
        self._save_notes()
        
        tasks = load_tasks()
        self.settings = load_settings()
        
        output = generate_wallpaper(self.selected_image, tasks, self.settings)
        
        if not output:
            self._update_status("❌ Failed")
            return
        
        if set_wallpaper(output):
            self._update_status("✅ Applied!")
            self._show_preview(output)
        else:
            self._update_status("❌ Could not set wallpaper")
    
    def _show_preview(self, path):
        from PIL import Image
        try:
            img = Image.open(path)
            ratio = min(900 / img.width, 550 / img.height)
            size = (int(img.width * ratio), int(img.height * ratio))
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            self.preview_img = ctk.CTkImage(light_image=img, dark_image=img, size=size)
            self.preview_label.configure(image=self.preview_img, text="")
            self.tabview.set("👁 Preview")
        except Exception as e:
            print(f"Preview error: {e}")
    
    def _open_images_folder(self):
        import subprocess
        IMAGES_DIR.mkdir(exist_ok=True)
        subprocess.run(['explorer', str(IMAGES_DIR)])
    
    def _update_status(self, msg):
        self.status_label.configure(text=msg)


def run_app():
    app = WallpaperCalendarApp()
    app.mainloop()


if __name__ == "__main__":
    run_app()
