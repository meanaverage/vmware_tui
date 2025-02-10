import curses
from typing import Optional
from ..utils.logging import log_message
from ..config.settings import (
    status_log, 
    hidden_vms
)
from ..config.themes import (
    get_themes,
    get_current_theme,  # Get theme functions from themes.py
    initialize_theme_colors,
    THEMES  # Add this import
)
from ..api.vm_get import get_vm_list
from .vm_menu import VMMenu
from ..utils.lock import menu_lock
from queue import Empty  # Add this import at the top
from .base_menu import BaseMenu

class MainMenu(BaseMenu):
    def __init__(self, stdscr):
        super().__init__(stdscr)  # This sets up themed windows
        self.current_row = 0
        self.vm_list = []
        self.draw_empty_screen()

    def setup_windows(self):
        """Initialize/reinitialize all windows."""
        height, width = self.stdscr.getmaxyx()
        main_height = height - 22  # Reduced to make room for API window
        api_height = 8            # API messages window
        status_height = 10        # Status messages
        
        # Create windows
        self.main_window = curses.newwin(main_height, width - 4, 2, 2)
        self.main_window.keypad(1)
        self.api_window = curses.newwin(api_height, width - 4, main_height + 2, 2)
        self.status_window = curses.newwin(status_height, width - 4, main_height + api_height + 2, 2)
        
        # Apply theme background
        theme = THEMES.get(get_current_theme(), THEMES["ubuntu"])
        attr = curses.color_pair(1)
        if theme.get("use_bold", True):
            attr |= curses.A_BOLD
        
        for window in [self.main_window, self.api_window, self.status_window]:
            window.bkgd(' ', attr)

    def refresh_vm_list(self, force: bool = False):
        """Refresh the list of VMs."""
        # This entire method should be called with menu_lock held
        old_count = len(self.vm_list)
        log_message(f"Starting VM list refresh (force={force})...", refresh=True)
        
        try:
            self.vm_list = get_vm_list(force)
            new_count = len(self.vm_list)
            log_message(f"VM list refresh complete. VMs: {old_count} -> {new_count}", refresh=True)
        finally:
            self.draw_screen()

    def handle_input(self, key) -> Optional[VMMenu]:
        """Handle keyboard input."""
        if key == curses.KEY_UP and self.current_row > 0:
            self.current_row -= 1
        elif key == curses.KEY_DOWN and self.current_row < len(self.vm_list) - 1:
            self.current_row += 1
        elif key in [curses.KEY_ENTER, ord('\n')] and self.vm_list:
            # Return a new VM menu for the selected VM
            selected_vm = self.vm_list[self.current_row]
            return VMMenu(self.stdscr, selected_vm['id'], selected_vm['name'])
        return None

    def get_display_status(self, status: str) -> str:
        """Convert API status to display status."""
        status = status.lower()
        if status == 'poweredon':
            return 'On'
        elif status == 'poweredoff':
            return 'Off'
        elif status == 'suspended':
            return 'Sus'
        return '???'

    def draw_screen(self):
        """Draw the main interface."""
        if self.vm_list:
            self.main_window.clear()
            
            # Draw main window border
            self.draw_box(self.main_window)
            
            # Get current theme directly from THEMES
            theme = THEMES.get(get_current_theme(), THEMES["ubuntu"])
            
            # Draw title and instructions
            max_y, max_x = self.main_window.getmaxyx()
            title = "VMware Manager"
            instructions = "↑/↓: Navigate | Enter: Select | c: Config | q: Quit"
            
            # Draw title with theme colors
            x = max_x//2 - len(title)//2
            self.main_window.attron(curses.color_pair(1))
            self.main_window.addstr(0, x, title, curses.A_BOLD)
            self.main_window.attroff(curses.color_pair(1))
            
            # Add instructions below title
            x = max_x//2 - len(instructions)//2
            self.main_window.addstr(1, x, instructions)
            
            # Draw separator
            self.main_window.addstr(2, 0, "─" * max_x)

            # Draw VM list
            visible_vms = [vm for vm in self.vm_list if vm.get('id') not in hidden_vms]
            
            name_start = 3
            status_start = name_start + 40

            for idx, vm in enumerate(visible_vms):
                if idx + 3 >= max_y:
                    break
                
                vm_name = vm.get('name', 'Unknown VM')
                status = vm.get('power_state', 'UNKNOWN')
                display_status = self.get_display_status(status)
                
                y_pos = idx + 3
                
                if idx == self.current_row:
                    # Selected item - just add a space before the name
                    self.main_window.addstr(y_pos, 2, " ")  # Single space indent
                    self.main_window.attron(curses.A_REVERSE)
                    self.main_window.addstr(y_pos, name_start, vm_name)
                    self.main_window.attroff(curses.A_REVERSE)
                else:
                    # Non-selected item - just add a space before the name
                    self.main_window.addstr(y_pos, 2, " ")  # Single space indent
                    self.main_window.addstr(y_pos, name_start, vm_name)
                
                # Use theme colors for power states
                if status.lower() == 'poweredon':
                    self.main_window.attron(curses.color_pair(2))  # Green
                    self.main_window.addstr(y_pos, status_start, f"[{display_status:^3}]")
                    self.main_window.attroff(curses.color_pair(2))
                elif status.lower() == 'poweredoff':
                    self.main_window.attron(curses.color_pair(3))  # Red
                    self.main_window.addstr(y_pos, status_start, f"[{display_status:^3}]")
                    self.main_window.attroff(curses.color_pair(3))

            self.main_window.refresh()

        # Collect any new messages
        self.collect_messages()
        
        # Draw API window with border
        self.api_window.clear()
        self.draw_box(self.api_window)
        self.api_window.addstr(0, 2, " API Calls ")
        
        # Show API messages
        max_x = self.api_window.getmaxyx()[1] - 4
        for i, msg in enumerate(self.api_messages[-6:]):
            try:
                # Extract timestamp and API call
                parts = msg.split(" - ", 2)  # Split into [level, timestamp, message]
                if len(parts) >= 3:
                    # Get timestamp without milliseconds
                    timestamp = parts[1].strip()  # e.g., "14:22:04"
                    api_call = parts[2].replace("API CALL: ", "").strip()
                    formatted_msg = f"{timestamp}  {api_call}"
                    self.api_window.addstr(i + 1, 2, formatted_msg[:max_x])
                else:
                    # Fallback - show raw message if parsing fails
                    self.api_window.addstr(i + 1, 2, msg[:max_x])
            except curses.error:
                pass
        
        self.api_window.refresh()
        
        # Draw status window with border
        self.status_window.clear()
        self.draw_box(self.status_window)
        self.status_window.addstr(0, 2, " Log Messages ")
        
        # Show log messages
        max_x = self.status_window.getmaxyx()[1] - 4
        for i, msg in enumerate(self.log_messages[-8:]):
            try:
                self.draw_colored_message(self.status_window, i + 1, 2, msg, max_x)
            except curses.error:
                pass
        
        self.status_window.refresh()

    def get_status_color(self, status: str) -> int:
        """Get the color pair for a VM status."""
        theme = THEMES.get(get_current_theme(), THEMES["ubuntu"])
        status = status.lower()
        
        if status == 'poweredon':
            return curses.color_pair(2)  # Uses theme's powered_on color
        elif status == 'poweredoff':
            return curses.color_pair(3)  # Uses theme's powered_off color
        elif status == 'suspended':
            return curses.color_pair(4)  # Could add suspended color to themes
        return curses.color_pair(1)  # Default theme text color

    def draw_empty_screen(self):
        """Draw initial empty screen with borders and basic layout."""
        try:
            # Clear everything first
            self.stdscr.clear()
            self.main_window.clear()
            self.api_window.clear()
            self.status_window.clear()
            
            # Get current theme colors and window dimensions
            theme = THEMES.get(get_current_theme(), THEMES["ubuntu"])
            max_y, max_x = self.main_window.getmaxyx()
            
            # Ensure we have enough space
            if max_y < 5 or max_x < 20:  # Minimum size check
                log_message("Terminal window too small", "ERROR")
                return
            
            try:
                self.main_window.box()
                title = "VMware Manager"
                instructions = "↑/↓: Navigate | Enter: Select | c: Config | q: Quit"
                
                # Safe string drawing with bounds checking
                x = max(0, min(max_x//2 - len(title)//2, max_x - len(title)))
                self.main_window.attron(curses.color_pair(1))
                self.main_window.addstr(0, x, title[:max_x-1], curses.A_BOLD)
                self.main_window.attroff(curses.color_pair(1))
                
                x = max(0, min(max_x//2 - len(instructions)//2, max_x - len(instructions)))
                self.main_window.addstr(1, x, instructions[:max_x-1])
                
                # Try Unicode separator first, fall back to ASCII if it fails
                try:
                    separator = "─" * (max_x - 1)
                    self.main_window.addstr(2, 0, separator)
                except curses.error:
                    separator = "-" * (max_x - 1)
                    self.main_window.addstr(2, 0, separator)
                
                # Draw window titles safely
                api_title = " API Calls "
                log_title = " Log Messages "
                
                self.draw_box(self.api_window)
                self.api_window.addstr(0, 2, api_title[:self.api_window.getmaxyx()[1]-4])
                
                self.draw_box(self.status_window)
                self.status_window.addstr(0, 2, log_title[:self.status_window.getmaxyx()[1]-4])
                
                # Force refresh of all windows
                self.stdscr.noutrefresh()
                self.main_window.noutrefresh()
                self.api_window.noutrefresh()
                self.status_window.noutrefresh()
                curses.doupdate()
                
            except curses.error as e:
                log_message(f"Curses error in draw_empty_screen: {str(e)}", "ERROR")
                
        except Exception as e:
            log_message(f"Error in draw_empty_screen: {str(e)}", "ERROR")

    def apply_theme(self) -> None:
        """Apply current theme and redraw."""
        self.stdscr.clear()
        self.main_window.clear()
        self.api_window.clear()  # Clear API window
        self.status_window.clear()
        self.draw_empty_screen()
        self.draw_screen()
        curses.doupdate()

    def handle_theme_change(self):
        """Handle theme changes by reinitializing colors and redrawing."""
        initialize_theme_colors()
        self.current_theme = get_themes()[get_current_theme()]
        
        # Clear all windows
        self.stdscr.clear()
        self.main_window.clear()
        self.api_window.clear()  # Clear API window
        self.status_window.clear()
        
        # Redraw everything
        self.draw_empty_screen()
        self.draw_screen()
        
        # Force update
        self.stdscr.refresh()
        curses.doupdate() 