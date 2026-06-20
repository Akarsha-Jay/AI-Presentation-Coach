"""
AI Presentation Coach - Main Entry Point
"""

import sys
import customtkinter as ctk

# Ensure src module paths resolve correctly
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.gesture_recognizer import GestureRecognizer
from ui.dashboard import DashboardApp

def main():
    # Set appearance and theme globally
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    # 1. Initialize the threaded background recognizer
    recognizer = GestureRecognizer()
    recognizer.start()
    
    # 2. Launch the UI Dashboard
    app = DashboardApp(recognizer)
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    try:
        app.mainloop()
    except KeyboardInterrupt:
        print("Interrupted by user, exiting...")
        app.on_closing()

if __name__ == "__main__":
    main()
