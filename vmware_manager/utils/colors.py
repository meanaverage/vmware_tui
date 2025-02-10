import curses
from ..config.themes import get_themes
from ..config.settings import initialized_themes
from ..utils.logging import log_message

def initialize_colors():
    """Initialize color pairs for the application."""
    curses.start_color()
    curses.use_default_colors()
    
    themes = get_themes()
    current_pair = 1
    log_message("Initializing color themes...")
    
    # Initialize theme-specific colors and store the pair numbers back in themes
    for theme_name, theme in themes.items():
        log_message(f"Setting up theme: {theme_name}")
        # Title colors
        curses.init_pair(current_pair, theme['title_fg'], theme['title_bg'])
        theme['title_pair'] = current_pair
        log_message(f"  {theme_name}: title_pair = {current_pair}")
        current_pair += 1
        
        # Status colors
        curses.init_pair(current_pair, theme['status_on'], -1)
        theme['status_on_pair'] = current_pair
        log_message(f"  {theme_name}: status_on_pair = {current_pair}")
        current_pair += 1
        
        curses.init_pair(current_pair, theme['status_off'], -1)
        theme['status_off_pair'] = current_pair
        log_message(f"  {theme_name}: status_off_pair = {current_pair}")
        current_pair += 1
        
        curses.init_pair(current_pair, theme['status_suspended'], -1)
        theme['status_suspended_pair'] = current_pair
        log_message(f"  {theme_name}: status_suspended_pair = {current_pair}")
        current_pair += 1
    
    # Store initialized themes back in settings
    initialized_themes.clear()  # Clear existing theme data
    initialized_themes.update(themes)
    log_message(f"Color themes initialized. Available themes: {', '.join(themes.keys())}") 