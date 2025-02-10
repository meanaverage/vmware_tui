import curses
from typing import Dict, Optional
from ..api.vm_get import get_vm_details, get_vm_power_state
from ..api.vm_put import vm_action
from ..utils.logging import log_message
from ..config.settings import status_log
from ..config.themes import THEMES, get_current_theme
import time
from queue import Empty
from .base_menu import BaseMenu


class VMMenu(BaseMenu):
    def __init__(self, stdscr, vm_id: str, vm_name: str):
        super().__init__(stdscr)
        self.vm_id = vm_id
        self.vm_name = vm_name
        self.current_row = 0
        self.options = [
            "Start VM",
            "Shutdown VM",  # Graceful shutdown first
            "Stop VM",      # Hard stop moved down
            "Suspend VM",
            "Back to Main Menu"
        ]
        self.cached_messages = []  # For log messages
        self.vm_messages = []      # For VM-specific messages
        self.api_messages = []     # For API requests/responses
        self.last_update = 0  # Add timestamp for last update
        self.update_interval = 5  # Update every 5 seconds
        self.update_vm_info()  # Initial update
        self.setup_windows()

    def setup_windows(self):
        """Initialize/reinitialize all windows."""
        height, width = self.stdscr.getmaxyx()
        main_height = height - 22  # Main window height
        vm_msg_height = 6        # VM messages window
        api_height = 8            # API messages window
        status_height = 6        # Status messages window
        
        # Create windows with proper spacing
        self.main_window = curses.newwin(main_height, width - 4, 2, 2)
        self.main_window.keypad(1)
        
        # VM Messages window first (right after main window)
        self.vm_messages_window = curses.newwin(vm_msg_height, width - 4, main_height + 2, 2)
        
        # API window after VM Messages
        self.api_window = curses.newwin(api_height, width - 4, main_height + vm_msg_height + 2, 2)
        
        # Status window last
        self.status_window = curses.newwin(status_height, width - 4, main_height + vm_msg_height + api_height + 2, 2)
        
        # Apply theme background
        theme = THEMES.get(get_current_theme(), THEMES["ubuntu"])
        attr = curses.color_pair(1)
        if theme.get("use_bold", True):
            attr |= curses.A_BOLD
        
        for window in [self.main_window, self.vm_messages_window, self.api_window, self.status_window]:
            window.bkgd(' ', attr)

    def add_vm_message(self, message: str):
        """Add a message to the VM Messages window."""
        self.vm_messages.append(message)
        if len(self.vm_messages) > 4:  # Keep only last 4 messages
            self.vm_messages = self.vm_messages[-4:]

    def add_api_message(self, message: str):
        """Add a message to the API Messages window."""
        # Get window width for wrapping
        max_width = self.api_window.getmaxyx()[1] - 6  # -6 for margins and border
        
        # Handle multi-line messages (like JSON responses)
        if '\n' in message:
            # For JSON responses, preserve formatting but clean up
            lines = message.split('\n')
            for line in lines:
                self.api_messages.append(line.strip())
        else:
            # For single line messages, wrap if needed
            wrapped_lines = []
            current_line = ''
            
            for word in message.split():
                if len(current_line) + len(word) + 1 <= max_width:
                    current_line += (word + ' ')
                else:
                    if current_line:
                        wrapped_lines.append(current_line.rstrip())
                    current_line = word + ' '
            if current_line:
                wrapped_lines.append(current_line.rstrip())
            
            # Add each wrapped line as a separate message
            for line in wrapped_lines:
                self.api_messages.append(line)
        
        # Keep only the last N messages
        if len(self.api_messages) > 14:
            self.api_messages = self.api_messages[-14:]

    def update_vm_info(self):
        """Update both VM details and power state."""
        current_time = time.time()
        if current_time - self.last_update >= self.update_interval:
            self.vm_details = get_vm_details(self.vm_id)
            self.power_state = get_vm_power_state(self.vm_id)
            self.last_update = current_time
            # Only log when power state actually changes
            if not hasattr(self, '_last_power_state') or self._last_power_state != self.power_state:
                log_message(f"VM power state changed to: {self.power_state}")
                self._last_power_state = self.power_state

    def draw(self):
        """Draw the VM menu interface."""
        # Periodic update check
        current_time = time.time()
        if current_time - self.last_update >= self.update_interval:
            self.update_vm_info()
        
        # Collect any new messages
        self.collect_messages()  # This is from BaseMenu
        
        # Clear windows
        self.main_window.clear()
        self.api_window.clear()
        self.vm_messages_window.clear()
        self.status_window.clear()
        
        # Get current theme
        theme = THEMES.get(get_current_theme(), THEMES["ubuntu"])
        
        # Draw title with theme colors
        max_y, max_x = self.main_window.getmaxyx()
        title = f"VM: {self.vm_name}"
        x = max_x//2 - len(title)//2
        self.main_window.attron(curses.color_pair(1))  # Use basic text color
        self.main_window.addstr(0, x, title, curses.A_BOLD)
        self.main_window.attroff(curses.color_pair(1))
        
        # Draw navigation
        navigation = "↑/↓: Navigate | Enter: Select | q: Back"
        x = max_x//2 - len(navigation)//2
        self.main_window.addstr(1, x, navigation)
        
        # Draw separator
        self.main_window.addstr(2, 0, "─" * max_x)
        
        # Draw options
        for idx, option in enumerate(self.options):
            x = max_x//2 - len(option)//2
            y = max_y//2 - len(self.options)//2 + idx
            
            if idx == self.current_row:
                self.main_window.attron(curses.A_REVERSE)
            self.main_window.addstr(y, x, option)
            if idx == self.current_row:
                self.main_window.attroff(curses.A_REVERSE)
        
        # Draw API window with border
        self.api_window.clear()
        self.draw_box(self.api_window)
        self.api_window.addstr(0, 2, " API Calls ")
        
        # Show API messages (raw format for VM menu)
        max_x = self.api_window.getmaxyx()[1] - 4
        for i, msg in enumerate(self.api_messages[-6:]):
            try:
                self.api_window.addstr(i + 1, 2, msg[:max_x])
            except curses.error:
                pass
        
        self.api_window.refresh()

        # Draw VM messages window
        self.vm_messages_window.clear()
        self.draw_box(self.vm_messages_window)
        self.vm_messages_window.addstr(0, 2, " VM Messages ")
        
        # First show VM details (first line only)
        if hasattr(self, 'vm_details'):
            status_line = []
            if hasattr(self, 'power_state'):
                # Start with "Power: "
                status = f"Power: "
                # Add the state with appropriate color
                self.vm_messages_window.addstr(1, 2, status)
                
                if self.power_state.lower() == 'poweredoff':
                    theme = THEMES.get(get_current_theme(), THEMES["ubuntu"])
                    self.vm_messages_window.attron(curses.color_pair(3))  # Use theme's powered_off color
                    self.vm_messages_window.addstr(1, 2 + len(status), self.power_state)
                    self.vm_messages_window.attroff(curses.color_pair(3))
                elif self.power_state.lower() == 'poweredon':
                    theme = THEMES.get(get_current_theme(), THEMES["ubuntu"])
                    self.vm_messages_window.attron(curses.color_pair(2))  # Use theme's powered_on color
                    self.vm_messages_window.addstr(1, 2 + len(status), self.power_state)
                    self.vm_messages_window.attroff(curses.color_pair(2))
                else:
                    self.vm_messages_window.addstr(1, 2 + len(status), self.power_state)
                
                # Calculate where to start the next part
                current_x = 2 + len(status) + len(self.power_state) + 3  # +3 for " | "
                
                # Add CPU and memory info
                if 'cpu' in self.vm_details and isinstance(self.vm_details['cpu'], dict):
                    processors = self.vm_details['cpu'].get('processors', 0)
                    cpu_info = f"CPU: {processors} cores"
                    self.vm_messages_window.addstr(1, current_x, " | " + cpu_info)
                    current_x += len(cpu_info) + 3
                
                if 'memory' in self.vm_details:
                    memory_info = f"Memory: {self.vm_details['memory']}MB"
                    self.vm_messages_window.addstr(1, current_x, " | " + memory_info)
        
        # Then show VM action messages (using remaining lines)
        max_x = self.vm_messages_window.getmaxyx()[1] - 6  # -6 for margins
        for i, msg in enumerate(self.vm_messages[-3:]):  # Show last 3 messages (leaving room for status)
            try:
                self.vm_messages_window.addstr(i + 2, 2, msg[:max_x])  # Start from line 2
            except curses.error:
                pass
        
        # Draw status window
        self.status_window.clear()
        self.draw_box(self.status_window)
        self.status_window.addstr(0, 2, " Log Messages ")
        
        # Show only non-API messages from the parent class's log_messages
        max_x = self.status_window.getmaxyx()[1] - 6  # -6 for margins
        non_api_messages = [msg for msg in self.log_messages[-3:]  # Use log_messages instead of cached_messages
                           if "API CALL:" not in msg]  # Filter out API messages
        
        for i, msg in enumerate(non_api_messages):
            try:
                self.status_window.addstr(i + 2, 2, msg[:max_x])  # Start from line 2
            except curses.error:
                pass
        
        # Refresh windows
        self.main_window.refresh()
        self.api_window.refresh()
        self.vm_messages_window.refresh()
        self.status_window.refresh()

    def handle_input(self, key) -> bool:
        """Handle user input in the VM menu."""
        if key == curses.KEY_UP and self.current_row > 0:
            self.current_row -= 1
        elif key == curses.KEY_DOWN and self.current_row < len(self.options) - 1:
            self.current_row += 1
        elif key in [curses.KEY_ENTER, ord('\n')]:
            return self.execute_option()
        return True

    def execute_option(self) -> bool:
        """Execute the selected option."""
        selected = self.options[self.current_row]
        
        if selected == "Back to Main Menu":
            return False
        elif selected in ["Start VM", "Shutdown VM", "Stop VM", "Suspend VM"]:
            # Extract the action, but handle shutdown specially
            action = selected.split()[0].lower()
            api_action = action
            if action == "shutdown":
                api_action = "stop"
            
            # Add and show messages immediately
            self.add_vm_message(f"Attempting to {action} VM...")
            log_message(f"Attempting to {action} VM: {self.vm_name}")
            self.draw()  # Draw immediately to show the attempt message
            
            try:
                is_hard = action == "stop"
                success = vm_action(self.vm_id, api_action, force=is_hard, menu=self)
                if success:
                    msg = f"Successfully initiated {action}"
                    log_message(f"Successfully initiated {action} for VM: {self.vm_name}")
                    self.add_vm_message(msg)
                else:
                    msg = f"Failed to {action} VM"
                    log_message(f"Failed to {action} VM: {self.vm_name}", "ERROR")
                    self.add_vm_message(msg)
            except Exception as e:
                msg = f"Error: {str(e)}"
                log_message(f"Error during {action} operation: {str(e)}", "ERROR")
                self.add_vm_message(msg)
            
            self.draw()  # Draw again after the action completes
        
        elif selected == "View Details":
            self.vm_details = get_vm_details(self.vm_id)
            if not self.vm_details:
                log_message(f"Failed to fetch details for VM {self.vm_name}", "ERROR")
        
        return True 