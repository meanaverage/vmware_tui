import os
import locale
import curses
import time
import threading
from typing import Optional
from vmware_manager.api.vm_get import get_vm_power_state
from vmware_manager.ui.main_menu import MainMenu
from vmware_manager.ui.config_menu import ConfigMenu
from vmware_manager.ui.vm_menu import VMMenu
from vmware_manager.config.settings import (
    menu_lock
)
from vmware_manager.utils.logging import log_message
import traceback
from .config.themes import initialize_theme_colors, get_current_theme, THEMES, load_themes
import atexit
import signal
import sys

# Global flag for clean shutdown
_SHUTDOWN_FLAG = False

def setup_locale():
    """Setup proper locale for UTF-8 support."""
    try:
        # Try to set the locale to the user's default with UTF-8
        locale.setlocale(locale.LC_ALL, '')
        
        # If that doesn't work, explicitly try UTF-8
        if not any(x in locale.getlocale()[1].lower() for x in ['utf', 'utf8', 'utf-8']):
            # Try common UTF-8 locales
            for loc in ['en_US.UTF-8', 'C.UTF-8', 'POSIX.UTF-8']:
                try:
                    locale.setlocale(locale.LC_ALL, loc)
                    break
                except locale.Error:
                    continue
        
        # Set environment variables as backup
        os.environ['LC_ALL'] = 'en_US.UTF-8'
        os.environ['LANG'] = 'en_US.UTF-8'
        
        log_message(f"Locale set to: {locale.getlocale()}")
    except Exception as e:
        log_message(f"Warning: Could not set locale: {str(e)}", "WARNING")

def cleanup_handler(signum=None, frame=None):
    """Handle cleanup on shutdown or signal."""
    global _SHUTDOWN_FLAG
    if _SHUTDOWN_FLAG:  # Prevent multiple cleanup attempts
        return
    _SHUTDOWN_FLAG = True
    
    log_message("Cleaning up application resources...")
    # Force cleanup any existing threads
    for thread in threading.enumerate():
        if thread.name == "VMRefreshWorker":
            try:
                thread.join(timeout=0.5)
            except:
                pass
    sys.exit(0)

def vm_refresh_worker(main_menu: MainMenu):
    """Background thread to update VM power states."""
    REFRESH_INTERVAL = 5
    POWER_STATE_INTERVAL = 10  # Power state checks every 10 seconds
    FULL_REFRESH_INTERVAL = 30  # Full refresh every 30 seconds
    last_full_refresh = 0
    last_power_check = 0
    
    # Add shutdown flag
    main_menu._shutdown = False
    
    while not main_menu._shutdown:
        try:
            current_time = time.time()
            
            if hasattr(main_menu, 'current_menu') and main_menu.current_menu is not None:
                time.sleep(REFRESH_INTERVAL)
                continue
            
            if menu_lock.acquire(timeout=1.0):
                try:
                    if not hasattr(main_menu, 'current_menu') or main_menu.current_menu is None:
                        if current_time - last_full_refresh >= FULL_REFRESH_INTERVAL:
                            main_menu.refresh_vm_list(force=True)
                            last_full_refresh = current_time
                        elif current_time - last_power_check >= POWER_STATE_INTERVAL:
                            # Just update power states
                            for vm in main_menu.vm_list:
                                vm_id = vm.get('id')
                                if vm_id:
                                    vm['power_state'] = get_vm_power_state(vm_id)
                            main_menu.draw_screen()
                            last_power_check = current_time
                finally:
                    menu_lock.release()
            
            time.sleep(REFRESH_INTERVAL)
            
        except Exception as e:
            log_message(f"Error in refresh worker: {str(e)}", "ERROR")
            if not main_menu._shutdown:
                time.sleep(1)

def apply_theme(stdscr):
    """Apply theme to the entire screen safely."""
    theme = THEMES.get(get_current_theme(), THEMES["ubuntu"])
    
    # Fill entire screen with theme background
    max_y, max_x = stdscr.getmaxyx()
    attr = curses.color_pair(1)  # Use color pair 1 for basic text
    if theme["use_bold"]:
        attr |= curses.A_BOLD
    
    try:
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

def main(stdscr):
    """Main application entry point."""
    try:
        # Register cleanup handlers
        atexit.register(cleanup_handler)
        signal.signal(signal.SIGINT, cleanup_handler)
        signal.signal(signal.SIGTERM, cleanup_handler)
        
        # Hide cursor
        curses.curs_set(0)
        
        # Load themes first, before any initialization
        log_message("Loading themes from config...")
        load_themes()
        
        log_message("Initializing curses and themes...")
        initialize_theme_colors()
        
        # Apply theme safely
        apply_theme(stdscr)  # Pass stdscr, not the theme name
        log_message(f"Theme initialization complete. Current theme: {get_current_theme()}")
        
        # Now create the UI with themes ready
        log_message("Creating main menu...")
        main_menu = MainMenu(stdscr)
        main_menu.current_menu = None  # Add this attribute to track current submenu
        current_menu: Optional[ConfigMenu | VMMenu] = None
        main_menu.draw_empty_screen()
        stdscr.refresh()
        
        # Initial VM list fetch (only done once)
        with menu_lock:
            log_message("Fetching initial VM list...", refresh=True)
            main_menu.refresh_vm_list(force=True)
            log_message("Initial VM list fetch complete", refresh=True)
        
        # Start the power state refresh thread
        refresh_thread = threading.Thread(
            target=vm_refresh_worker,
            args=(main_menu,),
            daemon=True,
            name="VMRefreshWorker"
        )
        refresh_thread.start()
        
        try:
            while not _SHUTDOWN_FLAG:
                # Shorter timeout for more responsive input
                stdscr.timeout(100)  # 100ms timeout for better responsiveness
                key = stdscr.getch()
                
                if current_menu:
                    main_menu.current_menu = current_menu  # Track active submenu
                    current_menu.draw()
                else:
                    main_menu.current_menu = None  # Clear submenu tracking
                    main_menu.draw_screen()
                
                if key == -1:  # No input
                    continue
                    
                if key == ord('q'):
                    break
                elif key == ord('c') and not current_menu:
                    log_message("Opening config menu...")
                    try:
                        log_message("Creating config menu instance...")
                        current_menu = ConfigMenu(stdscr, parent_menu=main_menu)
                        log_message("Config menu created successfully")
                        
                        log_message("Setting up config menu windows...")
                        current_menu.setup_windows()
                        log_message("Windows setup complete")
                        
                        log_message("Drawing initial config menu...")
                        current_menu.draw()
                        log_message("Initial draw complete")
                        
                        # Force screen update
                        curses.doupdate()
                        log_message("Screen update complete")
                        
                    except Exception as e:
                        log_message(f"Error creating config menu: {str(e)}", "ERROR")
                        log_message(f"Traceback: {traceback.format_exc()}", "ERROR")
                        current_menu = None  # Reset on error
                elif current_menu:
                    if not current_menu.handle_input(key):
                        log_message("Returning to main menu...")
                        current_menu = None
                        # Force a complete redraw of main menu when returning from config
                        initialize_theme_colors()  # Reinitialize colors
                        main_menu.draw_empty_screen()  # Draw empty screen first
                        main_menu.draw_screen()  # Then draw content
                        curses.doupdate()  # Force update
                else:
                    result = main_menu.handle_input(key)
                    if isinstance(result, VMMenu):
                        log_message(f"Opening VM menu for selected VM...")
                        current_menu = result
                
        finally:
            cleanup_handler()
            
    except Exception as e:
        log_message(f"Error in main function: {str(e)}", "ERROR")
        cleanup_handler()

def run():
    """Entry point for the application."""
    setup_locale()  # Setup locale before initializing curses
    curses.wrapper(main)

if __name__ == "__main__":
    run() 