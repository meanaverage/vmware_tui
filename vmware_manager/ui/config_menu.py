import curses
from typing import Dict
from ..config.settings import (
    INVERT_BACKGROUND,
    INVERT_TEXT,
    USER_THEMES,
    status_log,
    hidden_vms,
    menu_lock,
    initialized_themes,
    update_theme       # Keep this for saving to config
)
from ..config.themes import (
    get_themes, 
    invert_color, 
    initialize_theme_colors,
    apply_theme,
    get_current_theme,  # Get this from themes.py instead of settings.py
    THEMES,
    generate_random_theme,
    save_custom_theme,
    change_theme
)
from ..utils.logging import log_message
from queue import Empty
from ..api.vm_get import get_vm_list
from .base_menu import BaseMenu

class ConfigMenu(BaseMenu):
    def __init__(self, stdscr, parent_menu=None):
        log_message("Initializing config menu...")
        super().__init__(stdscr)
        self.parent_menu = parent_menu
        self.current_row = 0
        self.options = [
            "Change Theme",
            "Generate Random Theme",
            "Save Current Theme",
            "Delete Custom Theme",
            "Invert Background",
            "Invert Text",
            "Hide/Show VMs",
            "Back to Main Menu"
        ]
        self.theme_selection = 0
        self.in_theme_menu = False
        self.in_vm_selection = False
        self.vm_list = []
        self.cached_messages = []  # For log messages
        self.config_messages = []  # For config feedback
        log_message("Config menu initialization complete")

    def draw(self):
        """Draw the configuration menu."""
        # Clear all windows
        self.main_window.clear()
        self.config_window.clear()
        self.status_window.clear()

        # Get current theme directly from THEMES
        theme = THEMES.get(get_current_theme(), THEMES["ubuntu"])
        
        # Draw title with theme colors
        max_y, max_x = self.main_window.getmaxyx()
        title = "Configuration Menu"
        x = max_x//2 - len(title)//2
        self.main_window.attron(curses.color_pair(1))  # Use basic text color
        self.main_window.addstr(0, x, title, curses.A_BOLD)
        self.main_window.attroff(curses.color_pair(1))
        
        # Draw main window content
        max_y, max_x = self.main_window.getmaxyx()
        
        # Common navigation bar for all menus
        if self.in_theme_menu:
            title = "Select Theme"
            navigation = "↑/↓: Navigate | Enter: Select | q: Cancel"
        elif self.in_vm_selection:
            title = "Hide/Show VMs"
            navigation = "↑/↓: Navigate | Enter: Toggle Visibility"
        else:
            title = "Configuration Menu"
            navigation = "↑/↓: Navigate | Enter: Select | q: Exit"

        # Draw title and navigation
        x = max_x//2 - len(navigation)//2
        self.main_window.addstr(1, x, navigation)
        
        # Draw separator
        self.main_window.addstr(2, 0, "─" * max_x)

        if self.in_theme_menu:
            # Draw theme options
            theme_list = list(THEMES.keys())
            for idx, theme_name in enumerate(theme_list):
                x = max_x//2 - len(theme_name)//2
                y = max_y//2 - len(theme_list)//2 + idx + 2  # +2 for title and nav
                
                if idx == self.theme_selection:
                    self.main_window.attron(curses.A_REVERSE)
                try:
                    self.main_window.addstr(y, x, theme_name)
                except curses.error:
                    pass  # Skip if can't draw
                if idx == self.theme_selection:
                    self.main_window.attroff(curses.A_REVERSE)
        elif self.in_vm_selection:
            # Draw VM options
            # Find longest VM name for padding
            max_name_length = max(len(vm.get('name', 'Unknown')) for vm in self.vm_list)
            
            # Calculate left margin to center the list as a whole
            list_width = max_name_length + 4  # 4 for "[ ] " prefix
            left_margin = (max_x - list_width) // 2
            
            # Draw VMs and Back option
            display_items = self.vm_list + [None, {"name": "Back to Config Menu"}]  # Add None for spacing
            
            for idx, item in enumerate(display_items):
                if item is None:  # Skip the spacing line
                    continue
                    
                if idx < len(self.vm_list):  # Regular VM entry
                    vm = item
                    vm_name = vm.get('name', 'Unknown')
                    vm_id = vm.get('id')
                    prefix = "[H]" if vm_id in hidden_vms else "[ ]"
                    display_name = f"{prefix} {vm_name:<{max_name_length}}"
                    y = max_y//2 - len(display_items)//2 + idx + 2  # +2 for title and nav
                    
                    if idx == self.current_row:
                        self.main_window.attron(curses.A_REVERSE)
                    self.main_window.addstr(y, left_margin, display_name)
                    if idx == self.current_row:
                        self.main_window.attroff(curses.A_REVERSE)
                else:  # Back option
                    display_name = "Back to Config Menu"
                    # Center the back option
                    x = max_x//2 - len(display_name)//2
                    y = max_y//2 - len(display_items)//2 + idx + 2  # +2 for title and nav
                    
                    if idx == self.current_row:
                        self.main_window.attron(curses.A_REVERSE)
                    self.main_window.addstr(y, x, display_name)
                    if idx == self.current_row:
                        self.main_window.attroff(curses.A_REVERSE)
        else:
            # Draw main config options
            for idx, option in enumerate(self.options):
                x = max_x//2 - len(option)//2
                y = max_y//2 - len(self.options)//2 + idx + 2  # +2 for title and nav
                
                if idx == self.current_row:
                    self.main_window.attron(curses.A_REVERSE)
                self.main_window.addstr(y, x, option)
                if idx == self.current_row:
                    self.main_window.attroff(curses.A_REVERSE)

        # Draw config messages window
        self.config_window.box()
        self.config_window.addstr(0, 2, " Config Messages ")
        
        # Draw last 4 config messages
        for i, msg in enumerate(self.config_messages[-4:]):
            if i < 4:
                self.config_window.addstr(i + 1, 2, msg[:self.config_window.getmaxyx()[1]-4])

        # Draw status window and logs
        self.status_window.box()
        self.status_window.addstr(0, 2, " Log Messages ")
        
        # Get any new messages
        while True:
            try:
                msg = status_log.get_nowait()
                self.cached_messages.append(msg)
            except Empty:
                break
            except:
                break
        
        # Draw messages
        max_x = self.status_window.getmaxyx()[1] - 4
        messages_to_show = self.cached_messages[-8:] if self.cached_messages else []
        
        for i, msg in enumerate(reversed(messages_to_show)):
            try:
                self.status_window.addstr(i + 1, 2, msg[:max_x])
            except curses.error:
                pass

        # Refresh all windows
        self.main_window.refresh()
        self.config_window.refresh()
        self.status_window.refresh()

    def add_config_message(self, message: str):
        """Add a message to the config messages window."""
        self.config_messages.append(message)
        if len(self.config_messages) > 4:
            self.config_messages = self.config_messages[-4:]

    def handle_input(self, key) -> bool:
        """Handle user input in the config menu."""
        if self.in_theme_menu:
            return self.handle_theme_input(key)
        elif self.in_vm_selection:
            return self.handle_vm_selection(key)
        elif key == curses.KEY_UP and self.current_row > 0:
            self.current_row -= 1
        elif key == curses.KEY_DOWN and self.current_row < len(self.options) - 1:
            self.current_row += 1
        elif key in [curses.KEY_ENTER, ord('\n')]:
            return self.execute_option()
        elif key == ord('q'):  # Add quick exit
            return False
        return True

    def apply_theme_change(self, new_theme: str) -> None:
        """Apply theme change and redraw all windows."""
        try:
            if change_theme(new_theme):
                # Reinitialize colors
                initialize_theme_colors()
                
                # Apply theme to parent menu first
                if self.parent_menu:
                    self.parent_menu.apply_theme()
                
                # Apply to config menu
                self.apply_theme()
                
                # Force complete redraw
                self.draw()
                curses.doupdate()
                
                self.add_config_message(f"Theme changed to: {new_theme}")
            else:
                self.add_config_message("Failed to change theme")
            
        except Exception as e:
            log_message(f"Error applying theme change: {str(e)}", "ERROR")
            self.add_config_message(f"Failed to change theme: {str(e)}")

    def handle_theme_input(self, key) -> bool:
        """Handle input in the theme selection menu."""
        theme_list = list(THEMES.keys())  # Use THEMES directly instead of self.themes
        if key == curses.KEY_UP and self.theme_selection > 0:
            self.theme_selection -= 1
        elif key == curses.KEY_DOWN and self.theme_selection < len(theme_list) - 1:
            self.theme_selection += 1
        elif key in [curses.KEY_ENTER, ord('\n')]:
            selected_theme = theme_list[self.theme_selection]
            self.apply_theme_change(selected_theme)
            self.in_theme_menu = False
        elif key == ord('q'):
            self.in_theme_menu = False
            self.add_config_message("Theme selection cancelled")
        return True

    def handle_vm_selection(self, key) -> bool:
        """Handle input in the VM selection menu."""
        total_items = len(self.vm_list) + 2  # +2 for spacing and Back option
        
        if key == curses.KEY_UP and self.current_row > 0:
            self.current_row -= 1
            if self.current_row == len(self.vm_list):  # Skip the spacing
                self.current_row -= 1
        elif key == curses.KEY_DOWN and self.current_row < total_items - 1:
            self.current_row += 1
            if self.current_row == len(self.vm_list):  # Skip the spacing
                self.current_row += 1
        elif key in [curses.KEY_ENTER, ord('\n')]:
            if self.current_row > len(self.vm_list):  # Back option selected
                self.in_vm_selection = False
                self.current_row = 0
                self.add_config_message("VM visibility settings saved")
                return True
            else:  # VM toggle selected
                vm = self.vm_list[self.current_row]
                vm_id = vm.get('id')
                if vm_id:
                    if vm_id in hidden_vms:
                        hidden_vms.remove(vm_id)
                        self.add_config_message(f"Showing VM: {vm.get('name')}")
                    else:
                        hidden_vms.add(vm_id)
                        self.add_config_message(f"Hiding VM: {vm.get('name')}")
        return True

    def execute_option(self) -> bool:
        """Execute the selected option."""
        if self.options[self.current_row] == "Back to Main Menu":
            return False
        elif self.options[self.current_row] == "Hide/Show VMs":
            with menu_lock:
                log_message("Fetching VM list for visibility settings...")
                self.vm_list = get_vm_list()
                self.in_vm_selection = True
                self.current_row = 0  # Reset selection to first VM
                self.add_config_message("Select VMs to hide/show using Enter")
                return True
        elif self.options[self.current_row] == "Change Theme":
            self.in_theme_menu = True
            self.theme_selection = 0
            self.add_config_message("Select a theme using arrow keys")
        elif self.options[self.current_row] == "Invert Background":
            global INVERT_BACKGROUND
            INVERT_BACKGROUND = not INVERT_BACKGROUND
            state = "enabled" if INVERT_BACKGROUND else "disabled"
            self.add_config_message(f"Background inversion {state}")
        elif self.options[self.current_row] == "Invert Text":
            global INVERT_TEXT
            INVERT_TEXT = not INVERT_TEXT
            state = "enabled" if INVERT_TEXT else "disabled"
            self.add_config_message(f"Text inversion {state}")
        elif self.options[self.current_row] == "Generate Random Theme":
            new_theme = generate_random_theme()
            THEMES["random_current"] = new_theme
            change_theme("random_current")
            initialize_theme_colors()
            self.parent_menu.apply_theme()  # Apply to parent menu
            self.apply_theme()  # Apply to config menu
            self.add_config_message("Generated random theme. Use 'Save Current Theme' to keep it.")
        elif self.options[self.current_row] == "Save Current Theme":
            # Get current theme data
            current = THEMES.get(get_current_theme())
            if current:
                # Prompt for name
                name = "custom_" + str(len(THEMES))  # Simple naming for now
                if save_custom_theme(current, name):
                    self.add_config_message(f"Theme saved as: {name}")
                else:
                    self.add_config_message("Failed to save theme")
        elif self.options[self.current_row] == "Delete Custom Theme":
            self.show_delete_theme_menu()  # You'll need to implement this
        return True

    def get_theme_name(self):
        """Prompt user for theme name."""
        # Implement a text input dialog
        # Return the name or None if cancelled
        pass

    def show_delete_theme_menu(self):
        """Show menu of custom themes that can be deleted."""
        # Implement a menu showing only custom themes
        # Allow user to select one to delete
        pass

    def setup_windows(self):
        """Initialize/reinitialize all windows."""
        height, width = self.stdscr.getmaxyx()
        log_message(f"Setting up config menu windows. Screen size: {width}x{height}")
        
        try:
            # Calculate window heights
            main_height = height - 18  # Main window
            config_height = 6          # Config messages
            status_height = 10         # Status messages
            
            # Create windows
            self.main_window = curses.newwin(main_height, width - 4, 2, 2)
            self.main_window.keypad(1)
            self.config_window = curses.newwin(config_height, width - 4, main_height + 2, 2)
            self.status_window = curses.newwin(status_height, width - 4, main_height + 8, 2)
            
            # Apply theme background to all windows
            theme = THEMES.get(get_current_theme(), THEMES["ubuntu"])
            attr = curses.color_pair(1)  # Use color pair 1 for basic text
            if theme["use_bold"]:
                attr |= curses.A_BOLD
            
            self.main_window.bkgd(' ', attr)
            self.config_window.bkgd(' ', attr)
            self.status_window.bkgd(' ', attr)
            
            log_message("Windows created and themed")
            
        except Exception as e:
            log_message(f"Error in setup_windows: {str(e)}", "ERROR")
            raise