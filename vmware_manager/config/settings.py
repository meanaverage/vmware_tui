import curses
import threading
import json
import os
from typing import Set, Dict, Optional, Callable
from ..utils.shared import status_log  # Import from shared instead of creating
from queue import Queue
from ..utils.logging import log_message
from . import config  # Import from config package
from .themes import get_current_theme  # Only import what we need
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Replace status_log list with a thread-safe queue
menu_lock = threading.Lock()  # Keep for VM list updates only

# VMware Workstation REST API settings
VMWARE_API_URL = os.getenv('VMWARE_API_URL', 'http://localhost:8697/api/vms')
VMWARE_USERNAME = os.getenv('VMWARE_USERNAME')
VMWARE_PASSWORD = os.getenv('VMWARE_PASSWORD')

if not all([VMWARE_USERNAME, VMWARE_PASSWORD]):
    raise ValueError(
        "Missing required environment variables. "
        "Please copy .env.example to .env and fill in your credentials."
    )

# Shared Data
hidden_vms: Set[str] = set()  # Store VM IDs that should be hidden
vm_details: Dict[str, dict] = {}  # Maps VM ID to details (name, cpu, memory)

# Timing settings
POWER_STATE_REFRESH = 5  # Update power states every 5 seconds
UI_UPDATE_INTERVAL = 1.0  # Minimum time between UI updates

# File paths
CONFIG_FILE = 'vmware_config.json'

# User customization
USER_THEMES = {}  # For saved random themes 

# Add this near the top with other shared data
initialized_themes: Dict = {}  # Store initialized theme color pairs 

# Global variables for theme management
_current_theme = "default"  # Private variable for theme storage

def get_current_theme() -> str:
    """Get the current theme."""
    global _current_theme
    return _current_theme

def update_theme(new_theme: str):
    """Update current theme and save to config."""
    config.config['theme'] = new_theme
    save_config(config.config)

def load_config():
    """Load configuration from file."""
    config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
        except Exception as e:
            config = {}
    return config

def save_config(config):
    """Save configuration to file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        pass  # Silently fail config save

# Load config at startup
config = load_config()

# UI settings with persistence
INVERT_BACKGROUND = config.get('invert_background', False)
INVERT_TEXT = config.get('invert_text', False)

# Other settings
menu_lock = threading.Lock()
hidden_vms: Set[str] = set()
vm_details: Dict[str, dict] = {}
initialized_themes: Dict = {} 