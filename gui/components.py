"""
Reusable GUI Components
"""
import customtkinter as ctk
from datetime import datetime
from typing import Callable, Optional


class TaskCard(ctk.CTkFrame):
    """Individual task display card"""
    
    CATEGORY_COLORS = {
        "deadline": "#E74C3C",
        "important": "#F1C40F", 
        "birthday": "#9B59B6",
        "reminder": "#2ECC71",
        "default": "#95A5A6",
    }
    
    def __init__(
        self, 
        parent, 
        task: dict, 
        on_delete: Callable[[str], None],
        on_edit: Callable[[dict], None],
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        
        self.task = task
        self.on_delete = on_delete
        self.on_edit = on_edit
        
        self.configure(
            fg_color=("gray90", "gray20"),
            corner_radius=10
        )
        
        self._create_widgets()
    
    def _create_widgets(self):
        # Category indicator
        category = self.task.get("category", "default")
        color = self.CATEGORY_COLORS.get(category, self.CATEGORY_COLORS["default"])
        
        indicator = ctk.CTkFrame(
            self,
            width=6,
            height=50,
            fg_color=color,
            corner_radius=3
        )
        indicator.pack(side="left", padx=(10, 5), pady=10)
        indicator.pack_propagate(False)
        
        # Content frame
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(side="left", fill="both", expand=True, padx=5, pady=10)
        
        # Title
        title_label = ctk.CTkLabel(
            content,
            text=self.task.get("title", "Untitled"),
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        title_label.pack(fill="x")
        
        # Date and category
        try:
            date_obj = datetime.strptime(self.task.get("date", ""), "%Y-%m-%d")
            date_str = date_obj.strftime("%B %d, %Y")
        except:
            date_str = self.task.get("date", "No date")
        
        info_label = ctk.CTkLabel(
            content,
            text=f"{date_str} • {category.capitalize()}",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray60"),
            anchor="w"
        )
        info_label.pack(fill="x", pady=(2, 0))
        
        # Buttons frame
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(side="right", padx=10, pady=10)
        
        # Delete button
        delete_btn = ctk.CTkButton(
            buttons,
            text="✕",
            width=30,
            height=30,
            fg_color="transparent",
            hover_color=("#FFEBEE", "#3D1F1F"),
            text_color=("#E74C3C", "#E74C3C"),
            command=lambda: self.on_delete(self.task["id"])
        )
        delete_btn.pack(side="right")


class ImageThumbnail(ctk.CTkFrame):
    """Wallpaper image thumbnail with selection"""
    
    def __init__(
        self,
        parent,
        image_path: str,
        on_select: Callable[[str], None],
        is_selected: bool = False,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        
        self.image_path = image_path
        self.on_select = on_select
        self.is_selected = is_selected
        
        self.configure(
            fg_color=("gray85", "gray25"),
            corner_radius=10,
            cursor="hand2"
        )
        
        self._create_widgets()
        self._update_selection()
        
        # Bind click
        self.bind("<Button-1>", self._on_click)
    
    def _create_widgets(self):
        from PIL import Image, ImageTk
        from pathlib import Path
        
        # Load and resize image
        try:
            img = Image.open(self.image_path)
            img.thumbnail((150, 100), Image.Resampling.LANCZOS)
            
            # Convert to CTkImage
            self.ctk_image = ctk.CTkImage(
                light_image=img,
                dark_image=img,
                size=(150, 100)
            )
            
            self.image_label = ctk.CTkLabel(
                self,
                image=self.ctk_image,
                text=""
            )
            self.image_label.pack(padx=5, pady=5)
            self.image_label.bind("<Button-1>", self._on_click)
            
            # Filename
            filename = Path(self.image_path).stem
            if len(filename) > 18:
                filename = filename[:15] + "..."
            
            self.name_label = ctk.CTkLabel(
                self,
                text=filename,
                font=ctk.CTkFont(size=11)
            )
            self.name_label.pack(pady=(0, 5))
            self.name_label.bind("<Button-1>", self._on_click)
            
        except Exception as e:
            error_label = ctk.CTkLabel(self, text="Error", text_color="red")
            error_label.pack(pady=20)
    
    def _on_click(self, event=None):
        self.on_select(self.image_path)
    
    def _update_selection(self):
        if self.is_selected:
            self.configure(
                fg_color=("#3498DB", "#2980B9"),
                border_width=3,
                border_color=("#2980B9", "#3498DB")
            )
        else:
            self.configure(
                fg_color=("gray85", "gray25"),
                border_width=0
            )
    
    def set_selected(self, selected: bool):
        self.is_selected = selected
        self._update_selection()


class CategorySelector(ctk.CTkFrame):
    """Category selection widget"""
    
    CATEGORIES = ["deadline", "important", "birthday", "reminder"]
    COLORS = {
        "deadline": "#E74C3C",
        "important": "#F1C40F",
        "birthday": "#9B59B6", 
        "reminder": "#2ECC71",
    }
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.selected = ctk.StringVar(value="deadline")
        self.configure(fg_color="transparent")
        
        self._create_widgets()
    
    def _create_widgets(self):
        for i, cat in enumerate(self.CATEGORIES):
            color = self.COLORS[cat]
            
            btn = ctk.CTkRadioButton(
                self,
                text=cat.capitalize(),
                variable=self.selected,
                value=cat,
                fg_color=color,
                hover_color=color,
                border_color=color
            )
            btn.grid(row=0, column=i, padx=10, pady=5)
    
    def get(self) -> str:
        return self.selected.get()
    
    def set(self, value: str):
        if value in self.CATEGORIES:
            self.selected.set(value)
