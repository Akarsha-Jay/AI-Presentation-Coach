"""
splash.py

Provides a modern, borderless loading screen that runs while the heavy
TensorFlow models initialize in a background thread.
"""

import os
import threading
import customtkinter as ctk
from PIL import Image
from core.gesture_recognizer import GestureRecognizer
from ui.theme import Theme

class SplashScreen(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master_app = master
        
        # Borderless window
        self.overrideredirect(True)
        
        # Center splash screen (e.g. 600x400)
        w, h = 600, 400
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)
        self.geometry(f'{w}x{h}+{int(x)}+{int(y)}')
        self.configure(fg_color=Theme.COLORS["bg_base"])
        
        self.attributes('-topmost', True)
        
        # Setup UI
        self._setup_ui()
        
        # Start background loading
        self.recognizer = None
        threading.Thread(target=self._load_heavy_resources, daemon=True).start()
        
    def _setup_ui(self):
        # Load Logo
        try:
            logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "logo.png")
            logo_img = ctk.CTkImage(light_image=Image.open(logo_path), dark_image=Image.open(logo_path), size=(120, 120))
            logo_label = ctk.CTkLabel(self, image=logo_img, text="")
            logo_label.pack(pady=(60, 20))
        except Exception as e:
            print(f"[Splash] Could not load logo: {e}")
            logo_label = ctk.CTkLabel(self, text="AI", font=ctk.CTkFont(size=60, weight="bold"), text_color=Theme.COLORS["primary"])
            logo_label.pack(pady=(60, 20))
            
        # Title
        title = ctk.CTkLabel(self, text="AI Presentation Coach", font=Theme.font_h1(), text_color=Theme.COLORS["text_main"])
        title.pack(pady=(0, 5))
        
        subtitle = ctk.CTkLabel(self, text="Loading neural engine...", font=Theme.font_body(), text_color=Theme.COLORS["text_sub"])
        subtitle.pack(pady=(0, 40))
        
        # Progress Bar
        self.progress = ctk.CTkProgressBar(self, width=300, height=8, fg_color=Theme.COLORS["bg_surface"], progress_color=Theme.COLORS["primary"])
        self.progress.pack()
        self.progress.set(0)
        self.progress.start()
        
    def _load_heavy_resources(self):
        # Simulate loading steps for visual feedback
        self.after(0, lambda: self.progress.set(0.2))
        
        # This is the blocking call (loads TF)
        self.recognizer = GestureRecognizer()
        self.recognizer.start()
        
        self.after(0, lambda: self.progress.set(1.0))
        self.after(500, self._launch_main_app)
        
    def _launch_main_app(self):
        self.progress.stop()
        self.destroy()
        
        # Launch Dashboard
        self.master_app.start_dashboard(self.recognizer)
