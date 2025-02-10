import curses
from typing import Dict
from ..utils.logging import log_message
import json
import os
from pathlib import Path

# Define the config directory in user's home
CONFIG_DIR = os.path.expanduser("~/.config/vmware_manager")
THEMES_FILE = os.path.join(CONFIG_DIR, "themes.json")

# Default built-in themes that can't be modified
DEFAULT_THEMES = {
    "ubuntu": {
        "name": "Ubuntu Server",
        "background": curses.COLOR_BLUE,
        "text": curses.COLOR_WHITE,
        "powered_on": curses.COLOR_GREEN,
        "powered_off": curses.COLOR_RED,
        "selected": curses.COLOR_BLACK,
        "selected_bg": curses.COLOR_WHITE,
        "use_bold": True
    },
    "matrix": {
        "name": "Matrix",
        "background": curses.COLOR_BLACK,
        "text": curses.COLOR_GREEN,
        "powered_on": curses.COLOR_GREEN,
        "powered_off": curses.COLOR_RED,
        "selected": curses.COLOR_GREEN,
        "selected_bg": curses.COLOR_BLACK,
        "use_bold": True
    },
    "dracula": {
        "name": "Dracula",
        "background": curses.COLOR_MAGENTA,
        "text": curses.COLOR_WHITE,
        "powered_on": curses.COLOR_GREEN,
        "powered_off": curses.COLOR_RED,
        "selected": curses.COLOR_BLACK,
        "selected_bg": curses.COLOR_WHITE,
        "use_bold": True
    },
    "solarized": {
        "name": "Solarized",
        "background": curses.COLOR_CYAN,
        "text": curses.COLOR_BLACK,
        "powered_on": curses.COLOR_GREEN,
        "powered_off": curses.COLOR_RED,
        "selected": curses.COLOR_WHITE,
        "selected_bg": curses.COLOR_BLACK,
        "use_bold": True
    },
    "nord": {
        "name": "Nord",
        "background": curses.COLOR_CYAN,
        "text": curses.COLOR_WHITE,
        "powered_on": curses.COLOR_GREEN,
        "powered_off": curses.COLOR_RED,
        "selected": curses.COLOR_BLACK,
        "selected_bg": curses.COLOR_WHITE,
        "use_bold": True
    }
}

# Working copy of themes
THEMES = DEFAULT_THEMES.copy()
_current_theme = "ubuntu"  # Default theme

def ensure_config_dir():
    """Create config directory if it doesn't exist."""
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)

def save_themes():
    """Save custom themes and current theme selection to config file."""
    ensure_config_dir()
    
    # Only save custom themes (not built-in ones)
    custom_themes = {name: theme for name, theme in THEMES.items() 
                    if name not in DEFAULT_THEMES}
    
    config = {
        "current_theme": _current_theme,
        "custom_themes": custom_themes
    }
    
    with open(THEMES_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def load_themes():
    """Load themes from config file."""
    global THEMES, _current_theme
    
    # Start with default themes
    THEMES = DEFAULT_THEMES.copy()
    
    if os.path.exists(THEMES_FILE):
        try:
            with open(THEMES_FILE, 'r') as f:
                config = json.load(f)
                
            # Load custom themes
            if "custom_themes" in config:
                THEMES.update(config["custom_themes"])
            
            # Load current theme selection
            if "current_theme" in config and config["current_theme"] in THEMES:
                _current_theme = config["current_theme"]
                
        except Exception as e:
            log_message(f"Error loading themes: {str(e)}", "ERROR")
            # Fall back to defaults if there's an error

def change_theme(new_theme: str) -> bool:
    """Change the current theme."""
    global _current_theme
    
    if new_theme not in THEMES:
        return False
        
    _current_theme = new_theme
    save_themes()  # Save the selection
    return True

def initialize_theme_colors():
    """Initialize color pairs for themes."""
    log_message("Starting color pair initialization...")
    curses.start_color()
    curses.use_default_colors()

    theme = THEMES.get(get_current_theme(), THEMES["ubuntu"])
    bg = theme["background"]
    fg = theme["text"]

    try:
        # Initialize basic color pairs
        log_message("Initializing theme colors...")
        curses.init_pair(1, fg, bg)                  # Basic text
        curses.init_pair(2, theme["powered_on"], bg) # Status on
        curses.init_pair(3, theme["powered_off"], bg) # Status off
        curses.init_pair(4, theme["selected"], theme["selected_bg"]) # Selected item

        log_message("Color pair initialization complete")
    except Exception as e:
        log_message(f"Error initializing colors: {str(e)}", "ERROR")
        raise

def get_current_theme() -> str:
    """Get the current theme."""
    return _current_theme

def get_themes(force_refresh=False, theme=None) -> Dict:
    """Return available color themes."""
    global THEMES
    
    # Return cached themes unless force refresh
    if theme is not None and not force_refresh:
        return THEMES
        
    current_theme = theme if theme is not None else _current_theme
    log_message(f"Building theme cache. Current theme is: {current_theme}")
    
    return THEMES

def get_color_pairs() -> dict:
    """Define the actual color pairs."""
    return {
        # Default theme pairs
        1: (curses.COLOR_WHITE, -1),      # Title
        2: (curses.COLOR_WHITE, -1),      # Text
        3: (curses.COLOR_WHITE, -1),      # Border
        4: (curses.COLOR_BLACK, curses.COLOR_WHITE),  # Selected
        5: (curses.COLOR_GREEN, -1),      # Status on
        6: (curses.COLOR_RED, -1),        # Status off
        7: (curses.COLOR_YELLOW, -1),     # Status suspended
        
        # Ubuntu theme pairs
        8: (curses.COLOR_WHITE, curses.COLOR_MAGENTA),   # Title
        9: (curses.COLOR_WHITE, -1),                     # Text (normal white)
        10: (curses.COLOR_WHITE, -1),                    # Border
        11: (curses.COLOR_BLACK, curses.COLOR_WHITE),    # Selected
        12: (curses.COLOR_GREEN, -1),                    # Status on
        13: (curses.COLOR_RED, -1),                      # Status off
        14: (curses.COLOR_YELLOW, -1),                   # Status suspended
    }

def invert_color(color):
    """Invert a curses color."""
    color_map = {
        curses.COLOR_BLACK: curses.COLOR_WHITE,
        curses.COLOR_WHITE: curses.COLOR_BLACK,
        curses.COLOR_BLUE: curses.COLOR_YELLOW,
        curses.COLOR_YELLOW: curses.COLOR_BLUE,
        curses.COLOR_GREEN: curses.COLOR_MAGENTA,
        curses.COLOR_MAGENTA: curses.COLOR_GREEN,
        curses.COLOR_RED: curses.COLOR_CYAN,
        curses.COLOR_CYAN: curses.COLOR_RED
    }
    return color_map.get(color, color)

def debug_config():
    """Print current config state for debugging."""
    log_message("=== Current Config State ===")
    log_message(f"Config file: {THEMES_FILE}")
    log_message(f"Current theme: {_current_theme}")
    log_message(f"Config contents: {THEMES}")
    log_message("========================")

def save_custom_theme(theme_dict, name):
    """Save a custom theme to config."""
    if not name:
        return False
    
    # Don't allow overwriting built-in themes
    if name in ["ubuntu", "matrix", "dracula", "solarized", "nord"]:
        return False
        
    try:
        # Load existing custom themes
        custom_themes = THEMES
        
        # Add new theme
        custom_themes[name] = theme_dict
        
        # Update THEMES
        THEMES.update(custom_themes)
        log_message(f"Saved custom theme: {name}")
        return True
    except Exception as e:
        log_message(f"Error saving custom theme: {str(e)}", "ERROR")
        return False

def delete_custom_theme(name):
    """Delete a custom theme."""
    if name in THEMES and name not in ["ubuntu", "matrix", "dracula", "solarized", "nord"]:
        # Remove from THEMES
        del THEMES[name]
        
        # Save to config
        save_themes()
        return True
    return False

def apply_theme(stdscr) -> None:
    """Apply current theme to the screen."""
    try:
        theme = THEMES.get(get_current_theme(), THEMES["ubuntu"])
        
        # Fill entire screen with theme background
        max_y, max_x = stdscr.getmaxyx()
        attr = curses.color_pair(1)  # Use color pair 1 for basic text
        if theme.get("use_bold", True):
            attr |= curses.A_BOLD
        
        # Set background character and attribute
        stdscr.bkgd(' ', attr)
        
        # Fill screen line by line, being careful of boundaries
        for y in range(max_y):
            try:
                # Write one less than max_x to avoid errors
                stdscr.addstr(y, 0, ' ' * (max_x - 1), attr)
            except curses.error:
                pass  # Skip if we hit the bottom-right corner
        
        stdscr.refresh()
        
    except Exception as e:
        log_message(f"Error applying theme: {str(e)}", "ERROR")

def generate_random_theme():
    """Generate a random theme."""
    import random
    colors = [
        curses.COLOR_BLACK, curses.COLOR_BLUE, curses.COLOR_CYAN,
        curses.COLOR_GREEN, curses.COLOR_MAGENTA, curses.COLOR_RED,
        curses.COLOR_WHITE, curses.COLOR_YELLOW
    ]
    
    # Ensure background and text have good contrast
    background = random.choice(colors)
    text_colors = [c for c in colors if c != background]
    text = random.choice(text_colors)
    
    return {
        "name": "Random Theme",
        "background": background,
        "text": text,
        "powered_on": curses.COLOR_GREEN,
        "powered_off": curses.COLOR_RED,
        "selected": text,
        "selected_bg": background,
        "use_bold": random.choice([True, False])
    } 