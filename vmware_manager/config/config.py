import json
import os
from pathlib import Path
from ..utils.logging import log_message

class Settings:
    def __init__(self):
        # Use home directory for config
        self.file_path = os.path.join(str(Path.home()), '.vmware_manager_config.json')
        log_message(f"Using config file: {self.file_path}")
        self.data = {}  # Initialize empty dict first
        self.load()  # Then load from file

    def load(self):
        """Load config from file."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    loaded_data = json.load(f)
                    log_message(f"Loaded config: {loaded_data}")
                    self.data.update(loaded_data)
            except Exception as e:
                log_message(f"Error loading config: {e}", "ERROR")
        else:
            log_message(f"No config file found at {self.file_path}, creating new one")
            self.save()

    def save(self):
        """Save config to file and verify."""
        try:
            log_message(f"Saving config to {self.file_path}...")
            log_message(f"Config data to save: {self.data}")
            
            with open(self.file_path, 'w') as f:
                json.dump(self.data, f, indent=4)
            
            log_message("Config saved successfully")
                
        except Exception as e:
            log_message(f"Error saving config: {str(e)}", "ERROR")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def __setitem__(self, key, value):
        """Set a config value and save it."""
        log_message(f"Setting config[{key}] = {value}")
        self.data[key] = value
        self.save()

# Create a single instance
settings = Settings()

# Export the instance's methods directly
def get(key, default=None):
    return settings.get(key, default)

def save_config():
    return settings.save()

def __setitem__(key, value):
    settings[key] = value 