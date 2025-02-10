import json
import os

CONFIG_FILE = 'vmware_config.json'

class Config:
    def __init__(self):
        self.config = self.load_config()

    def load_config(self):
        """Load configuration from file."""
        config = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
            except Exception:
                config = {}
        return config

# Create global config instance
config = Config() 