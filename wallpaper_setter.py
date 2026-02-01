"""
Windows Wallpaper Setter - Sets desktop wallpaper using Windows API
"""
import ctypes
from pathlib import Path
import os


# Windows API constants
SPI_SETDESKWALLPAPER = 0x0014
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE = 0x02


def set_wallpaper(image_path: str) -> bool:
    """
    Set the Windows desktop wallpaper
    
    Args:
        image_path: Absolute path to the image file
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure absolute path
        abs_path = str(Path(image_path).absolute())
        
        # Verify file exists
        if not os.path.exists(abs_path):
            print(f"Wallpaper file not found: {abs_path}")
            return False
        
        # Use Windows API to set wallpaper
        result = ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER,
            0,
            abs_path,
            SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
        )
        
        return bool(result)
    
    except Exception as e:
        print(f"Error setting wallpaper: {e}")
        return False


def get_current_wallpaper() -> str:
    """
    Get the current desktop wallpaper path
    
    Returns:
        Path to current wallpaper, or empty string on error
    """
    try:
        import winreg
        
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Control Panel\Desktop",
            0,
            winreg.KEY_READ
        )
        
        value, _ = winreg.QueryValueEx(key, "Wallpaper")
        winreg.CloseKey(key)
        
        return value
    
    except Exception as e:
        print(f"Error getting current wallpaper: {e}")
        return ""


if __name__ == "__main__":
    # Test
    current = get_current_wallpaper()
    print(f"Current wallpaper: {current}")
