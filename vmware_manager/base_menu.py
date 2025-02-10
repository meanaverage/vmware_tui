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
    
    def draw_box(self, window):
        """Draw a consistent box around a window using Unicode characters."""
        height, width = window.getmaxyx()
        
        # Draw corners
        window.addstr(0, 0, self.BOX_CHARS['top_left'])
        window.addstr(0, width-1, self.BOX_CHARS['top_right'])
        window.addstr(height-1, 0, self.BOX_CHARS['bottom_left'])
        window.addstr(height-1, width-1, self.BOX_CHARS['bottom_right'])
        
        # Draw horizontal lines
        for x in range(1, width-1):
            window.addstr(0, x, self.BOX_CHARS['horizontal'])
            window.addstr(height-1, x, self.BOX_CHARS['horizontal'])
        
        # Draw vertical lines
        for y in range(1, height-1):
            window.addstr(y, 0, self.BOX_CHARS['vertical'])
            window.addstr(y, width-1, self.BOX_CHARS['vertical']) 