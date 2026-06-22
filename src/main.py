"""
AI Presentation Coach - Main Entry Point
"""

import sys
import customtkinter as ctk

# Ensure src module paths resolve correctly
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.settings import SettingsManager
from ui.dashboard import DashboardApp

def main():
    # 0. Load settings
    settings = SettingsManager()
    theme = settings.get("theme", "dark")
    
    # Set appearance and theme globally
    ctk.set_appearance_mode(theme)
    ctk.set_default_color_theme("blue")
    app = DashboardApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    import signal
    def handle_sigint(signum, frame):
        print("\nInterrupted by user, exiting...")
        app.on_closing()
        
    signal.signal(signal.SIGINT, handle_sigint)

    app.mainloop()

if __name__ == "__main__":
    main()
