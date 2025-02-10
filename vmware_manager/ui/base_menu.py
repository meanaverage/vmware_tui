import curses
from ..config.themes import get_themes, get_current_theme, THEMES
from ..config.settings import status_log
from ..utils.logging import log_message
from queue import Empty

class BaseMenu:
    # Add box drawing constants
    BOX_CHARS = {
        'horizontal': "─",
        'vertical': "│",
        'top_left': "┌",
        'top_right': "┐",
        'bottom_left': "└",
        'bottom_right': "┘",
    }
    
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.cached_messages = []  # All messages
        self.api_messages = []     # API messages only
        self.log_messages = []     # Non-API messages only
        theme_name = get_current_theme()
        self.current_theme = get_themes(theme=theme_name)[theme_name]  # Get the specific theme dictionary
        self.main_window = None
        self.status_window = None
        self.setup_windows()

    def setup_windows(self):
        """Initialize the windows."""
        height, width = self.stdscr.getmaxyx()
        main_height = height - 12  # Changed from 8 to 12 to make room for logs
        
        # Create windows
        self.main_window = curses.newwin(main_height, width - 4, 2, 2)
        self.main_window.keypad(1)  # Enable keypad for arrow keys
        self.status_window = curses.newwin(10, width - 4, main_height + 2, 2)
        
        # Apply theme background to each window
        self.apply_theme()

    def apply_theme(self):
        """Apply current theme to all windows."""
        theme = THEMES.get(get_current_theme(), THEMES["ubuntu"])
        attr = curses.color_pair(1)
        if theme.get("use_bold", True):
            attr |= curses.A_BOLD
        
        # Apply to all windows
        for window in [self.main_window, self.status_window]:
            if window:
                window.bkgd(' ', attr)
                window.refresh()

    def update_theme(self):
        """Update the cached theme."""
        self.current_theme = get_themes()[get_current_theme()]

    def draw_box(self, window):
        """Draw a consistent box around a window."""
        height, width = window.getmaxyx()
        
        try:
            # First try with Unicode box chars
            window.addch(0, 0, self.BOX_CHARS['top_left'])
            window.addch(0, width-1, self.BOX_CHARS['top_right'])
            window.addch(height-1, 0, self.BOX_CHARS['bottom_left'])
            window.addch(height-1, width-1, self.BOX_CHARS['bottom_right'])
            
            # Draw horizontal lines
            for x in range(1, width-1):
                window.addch(0, x, self.BOX_CHARS['horizontal'])
                window.addch(height-1, x, self.BOX_CHARS['horizontal'])
            
            # Draw vertical lines
            for y in range(1, height-1):
                window.addch(y, 0, self.BOX_CHARS['vertical'])
                window.addch(y, width-1, self.BOX_CHARS['vertical'])
            
        except curses.error:
            try:
                # Fall back to ASCII box drawing
                window.box()  # Use curses built-in box as first fallback
            except curses.error:
                try:
                    # Manual ASCII box as last resort
                    window.addch(0, 0, '+')
                    window.addch(0, width-1, '+')
                    window.addch(height-1, 0, '+')
                    window.addch(height-1, width-1, '+')
                    
                    for x in range(1, width-1):
                        window.addch(0, x, '-')
                        window.addch(height-1, x, '-')
                    
                    for y in range(1, height-1):
                        window.addch(y, 0, '|')
                        window.addch(y, width-1, '|')
                        
                except curses.error as e:
                    log_message(f"Failed to draw box: {str(e)}", "ERROR")

    def draw_status_window(self):
        """Draw the status window with non-API log messages."""
        self.status_window.clear()
        self.draw_box(self.status_window)
        self.status_window.addstr(0, 2, " Log Messages ")
        
        # Get any new messages
        self.collect_messages()
        
        # Draw non-API messages
        max_x = self.status_window.getmaxyx()[1] - 4
        messages_to_show = [msg for msg in self.log_messages[-8:] 
                           if "API CALL:" not in msg]  # Filter out API messages
        
        for i, msg in enumerate(messages_to_show):
            try:
                self.draw_colored_message(self.status_window, i + 1, 2, msg[:max_x], max_x)
            except curses.error:
                pass

        self.status_window.refresh()

    def draw_title(self, title: str, instructions: str):
        """Draw title and instructions with theme colors."""
        max_x = self.main_window.getmaxyx()[1]
        theme = THEMES.get(get_current_theme(), THEMES["ubuntu"])
        
        # Draw title
        x = max_x//2 - len(title)//2
        self.main_window.attron(curses.color_pair(1))
        self.main_window.addstr(0, x, title, curses.A_BOLD)
        self.main_window.attroff(curses.color_pair(1))
        
        # Draw instructions
        x = max_x//2 - len(instructions)//2
        self.main_window.addstr(1, x, instructions)
        
        # Draw separator
        self.main_window.addstr(2, 0, "─" * max_x)

    def draw_colored_message(self, window, y: int, x: int, message: str, max_width: int):
        """Draw a message with color for certain keywords."""
        try:
            # Check for power state keywords
            if 'poweredoff' in message.lower():
                window.attron(curses.color_pair(3))  # Red color pair
                window.addstr(y, x, message[:max_width])
                window.attroff(curses.color_pair(3))
            else:
                window.addstr(y, x, message[:max_width])
        except curses.error:
            pass

    def collect_messages(self):
        """Collect new messages from the queue."""
        while True:
            try:
                msg = status_log.get_nowait()
                self.cached_messages.append(msg)
                if "API CALL:" in msg:
                    self.api_messages.append(msg)  # Remove debug logging
                else:
                    self.log_messages.append(msg)
            except Empty:
                break
            except Exception as e:
                break  # Just break, don't log here

        # Keep message lists at reasonable sizes
        max_messages = 1000
        if len(self.cached_messages) > max_messages:
            self.cached_messages = self.cached_messages[-max_messages:]
        if len(self.api_messages) > max_messages:
            self.api_messages = self.api_messages[-max_messages:]
        if len(self.log_messages) > max_messages:
            self.log_messages = self.log_messages[-max_messages:] 