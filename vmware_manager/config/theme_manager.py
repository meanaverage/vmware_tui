class ThemeManager:
    def __init__(self):
        self.current_theme = "default"
        
    def get_theme(self):
        return self.current_theme
        
    def set_theme(self, new_theme):
        self.current_theme = new_theme

# Global instance
theme_manager = ThemeManager() 