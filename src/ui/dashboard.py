"""
Dashboard UI Module

Contains the CustomTkinter application logic, layout, and periodic polling loop
that updates the GUI with background thread data from the GestureRecognizer.
"""

import os
import sys
import csv
import time
import cv2
import numpy as np
import customtkinter as ctk
import pyautogui
from PIL import Image, ImageTk, ImageGrab
import shutil
from tkinter import filedialog

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

if sys.platform == "win32":
    import ctypes

# Import config (we are now in src/ui, so config is in the parent directory)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GESTURE_LABELS, CONFIDENCE_THRESHOLD
from core.settings import SettingsManager
from ui.theme import Theme

class AnimatedStatCard(ctk.CTkFrame):
    def __init__(self, master, icon, title, **kwargs):
        super().__init__(master, fg_color=Theme.COLORS["bg_surface"], corner_radius=10, **kwargs)
        
        self.title_label = ctk.CTkLabel(self, text=f"{icon}  {title}", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=Theme.COLORS["text_sub"])
        self.title_label.pack(anchor="w", padx=15, pady=(15, 5))
        
        self.value_label = ctk.CTkLabel(self, text="--", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"), text_color=Theme.COLORS["text_main"])
        self.value_label.pack(anchor="w", padx=15, pady=(0, 15))
        
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        
        # Bind to children so hover works over text too
        for child in self.winfo_children():
            child.bind("<Enter>", self._on_enter)
            child.bind("<Leave>", self._on_leave)
            
        self.current_value = "--"

    def _on_enter(self, event):
        self.configure(fg_color=Theme.COLORS["bg_surface_hover"])

    def _on_leave(self, event):
        self.configure(fg_color=Theme.COLORS["bg_surface"])

    def update_value(self, new_value, color=Theme.COLORS["text_main"]):
        if str(new_value) != str(self.current_value):
            self.current_value = new_value
            self.value_label.configure(text=new_value, text_color=Theme.COLORS["primary"])
            self.after(300, lambda: self.winfo_exists() and self.value_label.configure(text_color=color))
        else:
            self.value_label.configure(text_color=color)

class CircularGauge(ctk.CTkFrame):
    def __init__(self, master, title, size=120, **kwargs):
        super().__init__(master, fg_color=Theme.COLORS["bg_surface"], corner_radius=10, **kwargs)
        self.size = size
        
        self.title_label = ctk.CTkLabel(self, text=f"🎯  {title}", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=Theme.COLORS["text_sub"])
        self.title_label.pack(anchor="w", padx=15, pady=(15, 0))
        
        self.canvas = ctk.CTkCanvas(self, width=size, height=size, bg=Theme.COLORS["bg_surface"][1], highlightthickness=0)
        self.canvas.pack(pady=10)
        
        # Center percentage text
        self.value_text = self.canvas.create_text(size/2, size/2, text="0%", fill=Theme.COLORS["text_main"][1], font=("Segoe UI", 24, "bold"))
        
        self.current_value = 0.0
        self._draw_arc(0.0, "#333333") # Base track
        
    def _draw_arc(self, percentage, color):
        self.canvas.delete("foreground")
        
        # Draw background track
        padding = 15
        bbox = (padding, padding, self.size - padding, self.size - padding)
        self.canvas.create_arc(bbox, start=0, extent=359.9, style="arc", outline=Theme.COLORS["border"][1], width=8, tags="background")
        
        # Draw foreground progress
        extent = -(percentage * 359.9) # Negative to draw clockwise
        if percentage > 0:
            self.canvas.create_arc(bbox, start=90, extent=extent, style="arc", outline=color, width=8, tags="foreground")
            
    def update_value(self, confidence_float):
        self.current_value = confidence_float
        
        if confidence_float >= 0.85:
            color = "#00C896" # Green
        elif confidence_float >= 0.70:
            color = "#FFB020" # Orange
        else:
            color = "#FF5252" # Red
            
        self.canvas.itemconfig(self.value_text, text=f"{confidence_float:.0%}")
        self._draw_arc(confidence_float, color)

class DashboardApp(ctk.CTk):
    """Main Dashboard Window using CustomTkinter."""
    
    def __init__(self):
        super().__init__()
        
        self.recognizer = None
        self.title("AI Presentation Coach Dashboard")
        self.geometry("1600x750")
        
        from ui.theme import Theme
        self.configure(fg_color=Theme.COLORS["bg_base"])
        
        # Grid layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0) # Sidebar
        self.grid_columnconfigure(1, weight=1) # Main Content
        
        self.pages = {}
        self.nav_buttons = {}
        
        # Init state MUST come before setup_ui to prevent AttributeError
        self._init_state()
        self._setup_ui()
        self._setup_logging()
        
        self.withdraw() # Hide main window immediately
        
        # Show splash screen (passing self as master)
        from ui.splash import SplashScreen
        self.splash = SplashScreen(self)
        
    def start_dashboard(self, recognizer):
        """Called by SplashScreen when heavy resources are loaded."""
        self.recognizer = recognizer
        self.deiconify() # Show main window
        self.update_frame()
        
    def _setup_ui(self):
        """Initializes all GUI frames and labels."""
        # --- Sidebar ---
        self.sidebar_frame = ctk.CTkFrame(self, fg_color=Theme.COLORS["bg_surface"], corner_radius=0, width=250)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="AI Coach", font=Theme.font_h1(), text_color=Theme.COLORS["primary"])
        self.logo_label.pack(pady=(30, 30), padx=20, anchor="w")
        
        nav_items = [
            ("\uE80F", "Dashboard"),
            ("\uE9D9", "Gesture Analytics"),
            ("\uE81C", "Session History"),
            ("\uE713", "Settings"),
            ("\uE946", "About")
        ]
        
        for icon, name in nav_items:
            container = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
            container.pack(fill="x", padx=10, pady=3)
            
            indicator = ctk.CTkFrame(container, fg_color="transparent", width=4, height=32, corner_radius=2)
            indicator.pack(side="left", pady=3)
            
            btn = ctk.CTkButton(container, text=f"{icon}   {name}", anchor="w", fg_color="transparent", text_color=Theme.COLORS["text_sub"], hover_color=Theme.COLORS["bg_surface_hover"], font=Theme.font_h3(), height=32, command=lambda n=name: self.select_page(n))
            btn.pack(side="left", fill="x", expand=True, padx=(5,0))
            self.nav_buttons[name] = {"btn": btn, "indicator": indicator}
            
        # --- Main Container ---
        self.main_container = ctk.CTkFrame(self, fg_color=Theme.COLORS["bg_base"], corner_radius=0)
        self.main_container.grid(row=0, column=1, sticky="nsew")
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)
        
        # --- Pages ---
        self._setup_dashboard_page()
        self._setup_analytics_page()
        self._setup_history_page()
        self._setup_settings_page()
        self._setup_about_page()
        
        # Select default page
        self.select_page("Dashboard")

    def select_page(self, name):
        """Handles switching between pages and highlighting the active sidebar button."""
        # Update button colors & active indicators
        for btn_name, elements in self.nav_buttons.items():
            btn = elements["btn"]
            ind = elements["indicator"]
            
            if btn_name == name:
                btn.configure(fg_color=Theme.COLORS["bg_surface_hover"], text_color=Theme.COLORS["primary"])
                ind.configure(fg_color=Theme.COLORS["primary"])
            else:
                btn.configure(fg_color="transparent", text_color=Theme.COLORS["text_sub"])
                ind.configure(fg_color="transparent")
                
        # Fade transition logic (pseudo-fade by delaying drawing)
        for page_name, page_frame in self.pages.items():
            if page_name == name:
                self.after(50, lambda p=page_frame: self.winfo_exists() and p.grid(row=0, column=0, sticky="nsew"))
                if name == "Session History" and hasattr(self, "_update_history_page"):
                    self._update_history_page()
            else:
                page_frame.grid_forget()

    def _setup_placeholder_page(self, name):
        """Creates a placeholder frame for unfinished pages."""
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        label = ctk.CTkLabel(frame, text=f"{name} Page", font=ctk.CTkFont(family="Segoe UI", size=32, weight="bold"), text_color=Theme.COLORS["text_sub"])
        label.place(relx=0.5, rely=0.5, anchor="center")
        self.pages[name] = frame

    def _setup_history_page(self):
        """Initializes the Session History page layout."""
        self.history_page_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.pages["Session History"] = self.history_page_frame
        
        title = ctk.CTkLabel(self.history_page_frame, text="Session History", font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"), text_color=Theme.COLORS["text_main"])
        title.pack(anchor="w", padx=40, pady=(40, 20))
        
        self.history_scrollable = ctk.CTkScrollableFrame(self.history_page_frame, fg_color=Theme.COLORS["bg_surface"], corner_radius=15)
        self.history_scrollable.pack(fill="both", expand=True, padx=40, pady=(0, 40))
        
        # Header
        header_frame = ctk.CTkFrame(self.history_scrollable, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(header_frame, text="Time", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), width=120, anchor="w", text_color=Theme.COLORS["text_main"]).pack(side="left")
        ctk.CTkLabel(header_frame, text="Gesture", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), width=150, anchor="w", text_color=Theme.COLORS["text_main"]).pack(side="left")
        ctk.CTkLabel(header_frame, text="Confidence", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), width=120, anchor="w", text_color=Theme.COLORS["text_main"]).pack(side="left")
        ctk.CTkLabel(header_frame, text="Status", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), width=150, anchor="w", text_color=Theme.COLORS["text_main"]).pack(side="left")

        self.history_list_frame = ctk.CTkFrame(self.history_scrollable, fg_color="transparent")
        self.history_list_frame.pack(fill="both", expand=True, padx=10, pady=5)

    def _update_history_page(self):
        """Populates the Session History page with recent events."""
        if not hasattr(self, "history_list_frame") or not self.history_list_frame.winfo_exists():
            return
            
        for child in self.history_list_frame.winfo_children():
            child.destroy()
            
        for entry in reversed(self.session_history_log[-50:]):
            row = ctk.CTkFrame(self.history_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=5)
            
            hrs, rem = divmod(int(entry[0]), 3600)
            mins, secs = divmod(rem, 60)
            t_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
            
            ctk.CTkLabel(row, text=t_str, font=ctk.CTkFont(family="Segoe UI", size=15), width=120, anchor="w", text_color=Theme.COLORS["text_sub"]).pack(side="left")
            ctk.CTkLabel(row, text=entry[1], font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), width=150, anchor="w", text_color=Theme.COLORS["primary"]).pack(side="left")
            ctk.CTkLabel(row, text=f"{entry[2]:.0%}", font=ctk.CTkFont(family="Segoe UI", size=15), width=120, anchor="w", text_color=Theme.COLORS["text_sub"]).pack(side="left")
            status_color = Theme.COLORS["primary"] if entry[3] == "Success" else Theme.COLORS["error"]
            ctk.CTkLabel(row, text=entry[3], font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), width=150, anchor="w", text_color=status_color).pack(side="left")

    def _setup_about_page(self):
        """Initializes the About page layout."""
        self.about_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.pages["About"] = self.about_frame
        
        title = ctk.CTkLabel(self.about_frame, text="About AI Presentation Coach", font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"), text_color=Theme.COLORS["text_main"])
        title.pack(anchor="w", padx=40, pady=(40, 20))
        
        container = ctk.CTkFrame(self.about_frame, fg_color=Theme.COLORS["bg_surface"], corner_radius=15)
        container.pack(fill="both", expand=True, padx=40, pady=(0, 40))
        
        info_text = (
            "AI Presentation Coach v1.0\n\n"
            "This application uses computer vision and machine learning to detect hand gestures "
            "and map them to presentation controls like Next Slide, Previous Slide, and more.\n\n"
            "Features:\n"
            "• Real-time gesture recognition\n"
            "• Analytics dashboard for session tracking\n"
            "• Customizable gesture mappings\n"
            "• Light, Dark, and System themes\n\n"
            "Developed with Python, OpenCV, and CustomTkinter."
        )
        
        lbl = ctk.CTkLabel(container, text=info_text, font=ctk.CTkFont(family="Segoe UI", size=16), justify="left", text_color=Theme.COLORS["text_sub"], wraplength=800)
        lbl.pack(anchor="nw", padx=30, pady=30)

    def _setup_settings_page(self):
        """Initializes the Settings page layout."""
        self.settings_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.pages["Settings"] = self.settings_frame
        
        title = ctk.CTkLabel(self.settings_frame, text="Application Settings", font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"), text_color=Theme.COLORS["text_main"])
        title.pack(anchor="w", padx=40, pady=(40, 20))
        
        container = ctk.CTkScrollableFrame(self.settings_frame, fg_color=Theme.COLORS["bg_surface"], corner_radius=15)
        container.pack(fill="both", expand=True, padx=40, pady=(0, 40))
        
        def create_setting_row(parent, label_text):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=30, pady=15)
            lbl = ctk.CTkLabel(row, text=label_text, font=ctk.CTkFont(family="Segoe UI", size=16), text_color=Theme.COLORS["text_sub"])
            lbl.pack(side="left")
            return row
            
        ctk.CTkLabel(container, text="Core Options", font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"), text_color=Theme.COLORS["primary"]).pack(anchor="w", padx=20, pady=(20, 10))
        
        row_conf = create_setting_row(container, "Confidence Threshold")
        self.val_conf = ctk.CTkLabel(row_conf, text=f"{self.settings.get('confidence_threshold'):.2f}", width=40)
        self.val_conf.pack(side="right", padx=(10, 0))
        self.slider_conf = ctk.CTkSlider(row_conf, from_=0.50, to=0.99, command=lambda v: self.val_conf.configure(text=f"{v:.2f}"))
        self.slider_conf.set(self.settings.get("confidence_threshold"))
        self.slider_conf.pack(side="right")
        
        row_cool = create_setting_row(container, "Cooldown Duration (sec)")
        self.val_cool = ctk.CTkLabel(row_cool, text=f"{self.settings.get('cooldown_duration'):.1f}s", width=40)
        self.val_cool.pack(side="right", padx=(10, 0))
        self.slider_cool = ctk.CTkSlider(row_cool, from_=0.5, to=5.0, number_of_steps=45, command=lambda v: self.val_cool.configure(text=f"{v:.1f}s"))
        self.slider_cool.set(self.settings.get("cooldown_duration"))
        self.slider_cool.pack(side="right")
        
        row_cam = create_setting_row(container, "Webcam Index (Requires Restart)")
        self.combo_cam = ctk.CTkComboBox(row_cam, values=["0", "1", "2", "3"])
        self.combo_cam.set(str(self.settings.get("webcam_index")))
        self.combo_cam.pack(side="right")
        
        row_theme = create_setting_row(container, "Theme (Requires Restart)")
        self.combo_theme = ctk.CTkComboBox(row_theme, values=["dark", "light", "system"])
        self.combo_theme.set(self.settings.get("theme"))
        self.combo_theme.pack(side="right")
        
        ctk.CTkLabel(container, text="Gesture Mappings", font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"), text_color=Theme.COLORS["primary"]).pack(anchor="w", padx=20, pady=(30, 10))
        
        actions = ["Next Slide", "Prev Slide", "Start Presentation", "Pause Presentation", "End Presentation", "None"]
        self.mapping_vars = {}
        
        mappings = self.settings.get("gesture_mappings")
        for gesture in ["fist", "like", "peace", "stop", "palm"]:
            row = create_setting_row(container, f"Gesture: {gesture.upper()}")
            combo = ctk.CTkComboBox(row, values=actions, width=200)
            combo.set(mappings.get(gesture, "None"))
            combo.pack(side="right")
            self.mapping_vars[gesture] = combo
            
        btn_save = ctk.CTkButton(container, text="Save Settings", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), fg_color=Theme.COLORS["primary"], hover_color=Theme.COLORS["primary_hover"], height=40, command=self._save_settings_from_ui)
        btn_save.pack(pady=40)

    def _save_settings_from_ui(self):
        updates = {
            "confidence_threshold": self.slider_conf.get(),
            "cooldown_duration": self.slider_cool.get(),
            "webcam_index": int(self.combo_cam.get()),
            "theme": self.combo_theme.get(),
            "gesture_mappings": {g: c.get() for g, c in self.mapping_vars.items()}
        }
        self.settings.update_multiple(updates)
        ctk.set_appearance_mode(updates["theme"])
        self._show_feedback("SETTINGS SAVED!", Theme.COLORS["primary"])
        print("[Settings] Saved successfully.")

    def _setup_analytics_page(self):
        """Initializes the Analytics page layout with Matplotlib charts."""
        self.analytics_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.pages["Gesture Analytics"] = self.analytics_frame
        
        self.analytics_frame.grid_rowconfigure(0, weight=1) # Top cards
        self.analytics_frame.grid_rowconfigure(1, weight=3) # Bottom charts
        self.analytics_frame.grid_columnconfigure(0, weight=1)
        
        # Top Metrics Grid
        self.analytics_cards_container = ctk.CTkFrame(self.analytics_frame, fg_color="transparent")
        self.analytics_cards_container.grid(row=0, column=0, sticky="nsew", padx=20, pady=(20, 10))
        self.analytics_cards_container.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.analytics_cards = {}
        metrics = [
            ("🖐️", "Total Gestures Detected", 0, 0),
            ("✅", "Successful Commands", 0, 1),
            ("❌", "Rejected Gestures", 0, 2),
            ("📈", "Average Confidence", 1, 0),
            ("🏆", "Most Used Gesture", 1, 1),
            ("⏱️", "Session Duration", 1, 2)
        ]
        for icon, field, r, c in metrics:
            card = AnimatedStatCard(self.analytics_cards_container, icon, field)
            card.grid(row=r, column=c, padx=10, pady=10, sticky="nsew")
            self.analytics_cards[field] = card
            
        # Bottom Charts Grid
        self.charts_container = ctk.CTkFrame(self.analytics_frame, fg_color="transparent")
        self.charts_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=(10, 20))
        self.charts_container.grid_columnconfigure((0, 1, 2), weight=1)
        self.charts_container.grid_rowconfigure(0, weight=1)
        
        plt.style.use("dark_background")
        
        # Chart 1: Gesture Frequency
        self.fig1, self.ax1 = plt.subplots(figsize=(4, 3), dpi=100)
        self.fig1.patch.set_facecolor('#121212')
        self.ax1.set_facecolor('#1E1E1E')
        self.ax1.set_title("Gesture Frequency", color=Theme.COLORS["text_main"][1])
        self.canvas1 = FigureCanvasTkAgg(self.fig1, master=self.charts_container)
        self.canvas1.get_tk_widget().grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Chart 2: Confidence Trend
        self.fig2, self.ax2 = plt.subplots(figsize=(4, 3), dpi=100)
        self.fig2.patch.set_facecolor('#121212')
        self.ax2.set_facecolor('#1E1E1E')
        self.ax2.set_title("Confidence Trend", color=Theme.COLORS["text_main"][1])
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=self.charts_container)
        self.canvas2.get_tk_widget().grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        # Chart 3: Commands Over Time
        self.fig3, self.ax3 = plt.subplots(figsize=(4, 3), dpi=100)
        self.fig3.patch.set_facecolor('#121212')
        self.ax3.set_facecolor('#1E1E1E')
        self.ax3.set_title("Commands Over Time", color=Theme.COLORS["text_main"][1])
        self.canvas3 = FigureCanvasTkAgg(self.fig3, master=self.charts_container)
        self.canvas3.get_tk_widget().grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
        
        # Start chart update loop
        self._update_analytics_charts()

    def _update_analytics_charts(self):
        """Periodic loop to update analytics data and charts."""
        if not self.winfo_exists():
            return
        # Update Cards
        self.analytics_cards["Total Gestures Detected"].update_value(str(self.total_gestures_detected))
        self.analytics_cards["Successful Commands"].update_value(str(self.successful_commands))
        self.analytics_cards["Rejected Gestures"].update_value(str(self.rejected_commands))
        
        avg_conf = 0.0
        if len(self.session_history_log) > 0:
            avg_conf = sum([entry[2] for entry in self.session_history_log]) / len(self.session_history_log)
        self.analytics_cards["Average Confidence"].update_value(f"{avg_conf:.0%}")
        
        most_used = "--"
        if self.gesture_counts_total:
            most_used = max(self.gesture_counts_total, key=self.gesture_counts_total.get)
        self.analytics_cards["Most Used Gesture"].update_value(most_used)
        
        hrs, rem = divmod(int(self.session_duration), 3600)
        mins, secs = divmod(rem, 60)
        self.analytics_cards["Session Duration"].update_value(f"{hrs:02d}:{mins:02d}:{secs:02d}")
        
        # Update Chart 1: Bar Chart
        self.ax1.clear()
        self.ax1.set_title("Gesture Frequency", color=Theme.COLORS["text_main"][1])
        if self.gesture_counts_total:
            labels = list(self.gesture_counts_total.keys())
            values = list(self.gesture_counts_total.values())
            self.ax1.bar(labels, values, color=Theme.COLORS["primary"][1])
        self.fig1.tight_layout()
        self.canvas1.draw()
        
        # Update Chart 2: Confidence Line
        self.ax2.clear()
        self.ax2.set_title("Confidence Trend", color=Theme.COLORS["text_main"][1])
        if len(self.session_history_log) > 0:
            times = [entry[0] for entry in self.session_history_log]
            confs = [entry[2] for entry in self.session_history_log]
            self.ax2.plot(times, confs, color=Theme.COLORS["warning"][1], marker='.')
        self.fig2.tight_layout()
        self.canvas2.draw()
        
        # Update Chart 3: Commands Over Time
        self.ax3.clear()
        self.ax3.set_title("Commands Over Time", color=Theme.COLORS["text_main"][1])
        if len(self.session_history_log) > 0:
            times = [entry[0] for entry in self.session_history_log if entry[3] != "Rejected"]
            counts = range(1, len(times) + 1)
            if times:
                self.ax3.plot(times, counts, color=Theme.COLORS["error"][1])
        self.fig3.tight_layout()
        self.canvas3.draw()
        
        self.after(2000, self._update_analytics_charts)

    def _setup_dashboard_page(self):
        """Initializes the Dashboard page layout."""
        self.dashboard_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.pages["Dashboard"] = self.dashboard_frame
        
        self.dashboard_frame.grid_columnconfigure(0, weight=3) # Webcam
        self.dashboard_frame.grid_columnconfigure(1, weight=1) # Statistics Panel
        self.dashboard_frame.grid_columnconfigure(2, weight=1) # History
        self.dashboard_frame.grid_rowconfigure(0, weight=1)
        
        # 1. Webcam Frame
        self.video_frame = ctk.CTkFrame(self.dashboard_frame, fg_color=Theme.COLORS["bg_surface"], corner_radius=15)
        self.video_frame.grid(row=0, column=0, padx=(30, 15), pady=30, sticky="nsew")
        self.video_label = ctk.CTkLabel(self.video_frame, text="")
        self.video_label.pack(expand=True, fill="both", padx=15, pady=15)
        
        self.feedback_label = ctk.CTkLabel(self.video_frame, text="", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"), text_color=Theme.COLORS["primary"])
        self.feedback_label.pack(pady=(0, 15))
        
        # 2. Statistics Panel
        self.stats_frame = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
        self.stats_frame.grid(row=0, column=1, padx=15, pady=30, sticky="nsew")
        self.stats_label_title = ctk.CTkLabel(self.stats_frame, text="Real-Time Statistics", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"), text_color=Theme.COLORS["text_main"])
        self.stats_label_title.pack(pady=(0, 20))
        
        self.cards_container = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        self.cards_container.pack(fill="both", expand=True)
        self.cards_container.grid_columnconfigure(0, weight=1)
        self.cards_container.grid_columnconfigure(1, weight=1)
        
        self.cards = {}
        stat_fields = [
            ("🖐️", "Current Gesture", 0, 0),
            ("🎯", "Confidence", 0, 1),
            ("🎬", "Presentation Status", 1, 0),
            ("🖼️", "Current Slide", 1, 1),
            ("✅", "Commands Executed", 2, 0),
            ("⏱️", "Session Time", 2, 1)
        ]
        
        for icon, field, r, c in stat_fields:
            if field == "Confidence":
                card = CircularGauge(self.cards_container, field)
            else:
                card = AnimatedStatCard(self.cards_container, icon, field)
            card.grid(row=r, column=c, padx=8, pady=8, sticky="nsew")
            self.cards[field] = card
                
        # 3. History Panel
        self.history_frame = ctk.CTkFrame(self.dashboard_frame, fg_color=Theme.COLORS["bg_surface"], corner_radius=15)
        self.history_frame.grid(row=0, column=2, padx=(15, 30), pady=30, sticky="nsew")
        self.history_label_title = ctk.CTkLabel(self.history_frame, text="Recent History", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"), text_color=Theme.COLORS["text_main"])
        self.history_label_title.pack(pady=(20, 20))
        
        self.history_entries = []
        for i in range(5):
            entry = ctk.CTkLabel(self.history_frame, text="-", font=ctk.CTkFont(family="Segoe UI", size=15), text_color=Theme.COLORS["text_sub"])
            entry.pack(anchor="w", padx=25, pady=12)
            self.history_entries.append(entry)
            
        # 4. Test Controls Panel
        self.test_frame = ctk.CTkFrame(self.dashboard_frame, fg_color=Theme.COLORS["bg_surface"], corner_radius=15)
        self.test_frame.grid(row=1, column=0, columnspan=3, padx=30, pady=(0, 30), sticky="ew")
        self.test_label = ctk.CTkLabel(self.test_frame, text="Test Controls:", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), text_color=Theme.COLORS["text_main"])
        self.test_label.pack(side="left", padx=25, pady=15)
        
        btn_prev = ctk.CTkButton(self.test_frame, text="Prev Slide (FIST)", font=ctk.CTkFont(family="Segoe UI", weight="bold"), fg_color=Theme.COLORS["primary"], hover_color=Theme.COLORS["primary_hover"], text_color=Theme.COLORS["text_main"], corner_radius=8, command=lambda: self._execute_action("fist", manual=True))
        btn_prev.pack(side="left", padx=10, pady=15)
        
        btn_next = ctk.CTkButton(self.test_frame, text="Next Slide (LIKE)", font=ctk.CTkFont(family="Segoe UI", weight="bold"), fg_color=Theme.COLORS["primary"], hover_color=Theme.COLORS["primary_hover"], text_color=Theme.COLORS["text_main"], corner_radius=8, command=lambda: self._execute_action("like", manual=True))
        btn_next.pack(side="left", padx=10, pady=15)

    def _init_state(self):
        """Initializes application state tracking variables."""
        self.settings = SettingsManager()
        
        self.presentation_status = "Waiting"
        self.current_slide = 1
        self.total_slides = 10
        self.session_duration = 0.0
        self.last_update_time = time.time()
        self.cooldown_end_time = 0.0
        
        self.last_detected_gesture = "None"
        self.total_gestures_detected = 0
        self.confidences = []
        
        self.candidate_gesture = None
        self.consecutive_frames = 0
        self.locked_gesture = "--"
        self.recent_predictions = []
        
        self.gesture_history_data = []
        
        # Analytics Tracking
        self.session_history_log = [] # List of tuples: (time_offset, gesture, confidence, action_status)
        self.gesture_counts_total = {}
        
        # Performance tracking counters
        self.successful_commands = 0
        self.rejected_commands = 0
        self.frame_times = []
        self.fps_frame_times = []
        self._feedback_timer = None
        
        self.summary_shown = False
        
    def _get_active_window_title(self):
        if sys.platform == "win32":
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value
        return "Unknown"

    def _force_foreground(self, hwnd):
        """Forces a window to the foreground by attaching thread inputs if necessary."""
        if sys.platform == "win32":
            user32 = ctypes.windll.user32
            foreground_thread = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), None)
            target_thread = user32.GetWindowThreadProcessId(hwnd, None)
            
            if foreground_thread != target_thread and foreground_thread != 0:
                user32.AttachThreadInput(foreground_thread, target_thread, True)
                user32.SetForegroundWindow(hwnd)
                user32.AttachThreadInput(foreground_thread, target_thread, False)
            else:
                user32.SetForegroundWindow(hwnd)

    def _focus_powerpoint(self):
        """Attempts to find and focus a PowerPoint window.
        Returns "SLIDESHOW" if active presentation is found.
        Returns "EDIT" if normal PowerPoint window is found.
        Returns "NONE" if no PowerPoint is found.
        """
        if sys.platform == "win32":
            # 1. Try finding Slide Show
            hwnd = ctypes.windll.user32.FindWindowW("screenClass", None)
            if hwnd and ctypes.windll.user32.IsWindowVisible(hwnd):
                ctypes.windll.user32.ShowWindow(hwnd, 9)
                self._force_foreground(hwnd)
                return "SLIDESHOW"
            
            # 2. Try finding PowerPoint Edit Window
            hwnd_edit = ctypes.windll.user32.FindWindowW("PPTFrameClass", None)
            if hwnd_edit and ctypes.windll.user32.IsWindowVisible(hwnd_edit):
                ctypes.windll.user32.ShowWindow(hwnd_edit, 9)
                self._force_foreground(hwnd_edit)
                return "EDIT"
                
        return "NONE"
        
    def _show_feedback(self, text, color=Theme.COLORS["warning"]):
        """Displays feedback on the dashboard and clears it after 3 seconds."""
        self.feedback_label.configure(text=text, text_color=color)
        if self._feedback_timer:
            self.after_cancel(self._feedback_timer)
        self._feedback_timer = self.after(3000, lambda: self.winfo_exists() and self.feedback_label.configure(text=""))

    def _setup_logging(self):
        """Creates a timestamped CSV session log in the logs directory."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(script_dir))
        logs_dir = os.path.join(project_root, 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        session_ts = time.strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(logs_dir, f"session_{session_ts}.csv")
        self.csv_file = open(log_path, 'w', newline='', encoding='utf-8')
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(["Timestamp", "Gesture", "Confidence", "Action", "Slide Number"])
        self.csv_file.flush()
        print(f"Session log: {log_path}")

    def _export_csv(self):
        """Copies the session CSV log to a user-selected path."""
        target_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if target_path and hasattr(self, "csv_file") and not self.csv_file.closed:
            self.csv_file.flush()
            shutil.copy(self.csv_file.name, target_path)
            print(f"[Export] Saved CSV to {target_path}")

    def _export_image_or_pdf(self, ext=".png"):
        """Takes a screenshot of the summary overlay and saves it."""
        target_path = filedialog.asksaveasfilename(defaultextension=ext, filetypes=[(f"{ext.upper()[1:]} files", f"*{ext}")])
        if target_path and hasattr(self, "summary_frame"):
            self.update_idletasks()
            x = self.summary_frame.winfo_rootx()
            y = self.summary_frame.winfo_rooty()
            w = self.summary_frame.winfo_width()
            h = self.summary_frame.winfo_height()
            
            img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
            if ext == ".pdf":
                img.save(target_path, "PDF", resolution=100.0)
            else:
                img.save(target_path)
            print(f"[Export] Saved {ext} to {target_path}")

    def _build_summary_overlay(self):
        """Builds and displays a full-screen overlay for the session summary."""
        self.summary_shown = True
        
        self.summary_overlay = ctk.CTkFrame(self.main_container, fg_color=Theme.COLORS["bg_base"], corner_radius=0)
        self.summary_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        self.summary_frame = ctk.CTkFrame(self.summary_overlay, fg_color=Theme.COLORS["bg_surface"], corner_radius=15, width=600, height=500)
        self.summary_frame.place(relx=0.5, rely=0.5, anchor="center")
        self.summary_frame.grid_propagate(False)
        
        title = ctk.CTkLabel(self.summary_frame, text="Session Complete", font=ctk.CTkFont(family="Segoe UI", size=32, weight="bold"), text_color=Theme.COLORS["primary"])
        title.pack(pady=(30, 20))
        
        hrs, rem = divmod(int(self.session_duration), 3600)
        mins, secs = divmod(rem, 60)
        duration_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
        
        avg_conf = sum([e[2] for e in self.session_history_log]) / len(self.session_history_log) if self.session_history_log else 0.0
        max_conf = max([e[2] for e in self.session_history_log]) if self.session_history_log else 0.0
        min_conf = min([e[2] for e in self.session_history_log]) if self.session_history_log else 0.0
        most_used = max(self.gesture_counts_total, key=self.gesture_counts_total.get) if self.gesture_counts_total else "--"
        
        metrics = [
            (f"Duration:", duration_str),
            (f"Commands Executed:", str(self.successful_commands)),
            (f"Average Confidence:", f"{avg_conf:.0%}"),
            (f"Highest Confidence:", f"{max_conf:.0%}"),
            (f"Lowest Confidence:", f"{min_conf:.0%}"),
            (f"Most Used Gesture:", most_used)
        ]
        
        metrics_frame = ctk.CTkFrame(self.summary_frame, fg_color="transparent")
        metrics_frame.pack(fill="x", padx=50, pady=20)
        
        for i, (label_text, val_text) in enumerate(metrics):
            lbl = ctk.CTkLabel(metrics_frame, text=label_text, font=ctk.CTkFont(family="Segoe UI", size=18), text_color=Theme.COLORS["text_sub"])
            lbl.grid(row=i//2, column=(i%2)*2, sticky="w", pady=10)
            val = ctk.CTkLabel(metrics_frame, text=val_text, font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color=Theme.COLORS["text_main"])
            val.grid(row=i//2, column=(i%2)*2+1, sticky="e", padx=(10, 30), pady=10)
            metrics_frame.grid_columnconfigure((i%2)*2, weight=1)
            metrics_frame.grid_columnconfigure((i%2)*2+1, weight=1)
            
        btn_frame = ctk.CTkFrame(self.summary_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=50, pady=(20, 30))
        
        btn_csv = ctk.CTkButton(btn_frame, text="Export CSV", fg_color=Theme.COLORS["bg_surface_hover"], hover_color=Theme.COLORS["border"], command=self._export_csv)
        btn_csv.pack(side="left", padx=10, expand=True)
        
        btn_png = ctk.CTkButton(btn_frame, text="Save Screenshot", fg_color=Theme.COLORS["bg_surface_hover"], hover_color=Theme.COLORS["border"], command=lambda: self._export_image_or_pdf(".png"))
        btn_png.pack(side="left", padx=10, expand=True)
        
        btn_pdf = ctk.CTkButton(btn_frame, text="Export PDF", fg_color=Theme.COLORS["bg_surface_hover"], hover_color=Theme.COLORS["border"], command=lambda: self._export_image_or_pdf(".pdf"))
        btn_pdf.pack(side="left", padx=10, expand=True)
        
        btn_close = ctk.CTkButton(self.summary_frame, text="Close Report", fg_color=Theme.COLORS["error"], hover_color=Theme.COLORS["error"], command=self.summary_overlay.destroy)
        btn_close.pack(pady=10)

    def update_frame(self):
        """
        Periodic GUI loop called via Tkinter's `after()`.
        Fetches the latest data from the background thread and redraws the UI.
        """
        if not self.winfo_exists():
            return
            
        # Fetch data safely from background worker thread
        frame, predictions, proc_ms = self.recognizer.get_latest_data()
        
        if frame is not None and predictions is not None:
            current_time = time.time()
            dt = current_time - self.last_update_time
            self.last_update_time = current_time
            
            # --- Timer updates ---
            if self.presentation_status == "Running":
                self.session_duration += dt
            hrs, rem = divmod(int(self.session_duration), 3600)
            mins, secs = divmod(rem, 60)
            duration_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
            
            is_cooldown = current_time < self.cooldown_end_time
                
            # --- Performance Logic ---
            self.frame_times.append(proc_ms)
            if len(self.frame_times) > 30:
                self.frame_times.pop(0)
            avg_proc = sum(self.frame_times) / len(self.frame_times)
            
            self.fps_frame_times.append(current_time)
            self.fps_frame_times = [t for t in self.fps_frame_times if current_time - t <= 1.0]
            fps = len(self.fps_frame_times)
            
            # --- Inference parsing ---
            top_idx = np.argmax(predictions)
            confidence = predictions[top_idx]
            
            if top_idx < len(GESTURE_LABELS):
                label = GESTURE_LABELS[top_idx]
            else:
                label = f"Class {top_idx}"
                
            # Note: FPS and Inference Time are now only shown in HUD
            self.cards["Commands Executed"].update_value(str(self.successful_commands))
            self.cards["Current Slide"].update_value(f"{self.current_slide} / {self.total_slides}")
            
            # --- State and stabilization logic ---
            threshold = self.settings.get("confidence_threshold", 0.70)
            current_label_upper = label.upper() if confidence >= threshold else "NONE"
            self.recent_predictions.append(current_label_upper)
            
            # Keep a sliding window of 7 frames (~230ms at 30fps) for fast majority voting
            if len(self.recent_predictions) > 7:
                self.recent_predictions.pop(0)
                
            # Count occurrences
            gesture_counts = {}
            for g in self.recent_predictions:
                gesture_counts[g] = gesture_counts.get(g, 0) + 1
                
            # Find the gesture with the highest count
            most_common_gesture = max(gesture_counts, key=gesture_counts.get)
            most_common_count = gesture_counts[most_common_gesture]
            
            # Require 4 out of 7 frames (majority) to lock in
            if most_common_count >= 4:
                if most_common_gesture != self.locked_gesture:
                    if most_common_gesture != "NONE" and self.locked_gesture != "--":
                        self.total_gestures_detected += 1
                        self.last_detected_gesture = self.locked_gesture
                        
                    self.locked_gesture = most_common_gesture
                    
                    if self.locked_gesture != "NONE":
                        self.confidences.append(confidence)
                        if len(self.confidences) > 100:
                            self.confidences.pop(0)
                        avg_conf = sum(self.confidences) / len(self.confidences)
                        # Average confidence metric removed from main UI
                        
                        
                        self._execute_action(self.locked_gesture.lower(), confidence=confidence, manual=False)
                    
            if self.locked_gesture != "NONE" and self.locked_gesture != "--":
                self.cards["Current Gesture"].update_value(self.locked_gesture)
                display_text = f"{label.upper()}: {confidence:.0%} (Live)"
            else:
                self.cards["Current Gesture"].update_value("UNKNOWN")
                display_text = f"UNKNOWN: {confidence:.0%} (Live)"
                
            # --- Global Label Colors ---
            status_color = "white"
            if self.presentation_status == "Running":
                status_color = Theme.COLORS["primary"] # Accent
            elif self.presentation_status == "Paused":
                status_color = Theme.COLORS["warning"] # Warning
            elif self.presentation_status == "Stopped":
                status_color = Theme.COLORS["error"] # Error
                if not getattr(self, "summary_shown", False):
                    self._build_summary_overlay()
                
            self.cards["Confidence"].update_value(confidence)
            self.cards["Presentation Status"].update_value(self.presentation_status, color=status_color)
            self.cards["Session Time"].update_value(duration_str)
            
            # --- Draw UI on Video Frame ---
            # Determine HUD color
            threshold = self.settings.get("confidence_threshold", 0.70)
            if label.upper() == "NONE":
                hud_color = (82, 82, 255) # Red (BGR)
            elif confidence < threshold:
                hud_color = (32, 176, 255) # Yellow (BGR)
            else:
                hud_color = (150, 200, 0) # Green (BGR)

            # Draw thick glowing border
            cv2.rectangle(frame, (0, 0), (frame.shape[1]-1, frame.shape[0]-1), hud_color, 8)

            # Draw semi-transparent HUD container at the top
            overlay = frame.copy()
            hud_height = 60
            cv2.rectangle(overlay, (0, 0), (frame.shape[1], hud_height), (20, 20, 20), -1)
            # Alpha blend the container
            alpha = 0.7
            frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

            # Draw status indicator circle
            cv2.circle(frame, (35, 30), 8, hud_color, -1)
            
            # Draw HUD Text
            hud_text = f"GESTURE: {label.upper()}  |  CONF: {confidence:.0%}  |  FPS: {fps}"
            cv2.putText(
                img=frame,
                text=hud_text,
                org=(60, 38),
                fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                fontScale=0.7,
                color=(255, 255, 255),
                thickness=2,
                lineType=cv2.LINE_AA
            )
            
            # Fast OpenCV BGR -> RGB Tkinter Conversion
            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv2image)
            imgtk = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
            
            self.video_label.configure(image=imgtk)
            self.video_label.image = imgtk
            
        # Re-schedule update at ~30 FPS (33ms)
        self.after(33, self.update_frame)

    def _execute_action(self, gesture, confidence=1.0, manual=False):
        """Handles the presentation control pipeline for a given gesture."""
        current_time = time.time()
        is_cooldown = current_time < self.cooldown_end_time
        action = "None"
        key_sent = "None"
        feedback_text = ""
        feedback_color = "white"
        
        print("\n--- ACTION PIPELINE EXECUTION ---")
        print(f"[DEBUG] Gesture Detected: {gesture.upper()}{' (MANUAL)' if manual else ''}")
        print(f"[DEBUG] Gesture Stabilized: {self.locked_gesture if not manual else gesture.upper()}")
        print(f"[DEBUG] Presentation State: {self.presentation_status}")
        print(f"[DEBUG] Cooldown Active: {is_cooldown}")
        
        if not is_cooldown or manual:
            ppt_status = self._focus_powerpoint()
            ppt_active = (ppt_status == "SLIDESHOW")
            time.sleep(0.1) # Small delay to ensure focus is applied
            active_win = self._get_active_window_title()
            print(f"[DEBUG] Active Window: {active_win}")
            
            mapping = self.settings.get("gesture_mappings", {})
            action_intent = mapping.get(gesture, "None")
            
            # Intelligent Fallback: If they trigger Next Slide but PowerPoint is only in Edit mode,
            # gracefully assume they want to Start the Presentation first!
            if action_intent == "Next Slide" and ppt_status == "EDIT":
                action_intent = "Start Presentation"
                
            if action_intent == "Start Presentation":
                self.summary_shown = False
                if not ppt_active:
                    self.presentation_status = "Running"
                    action = "Started"
                    key_sent = "f5"
                    pyautogui.press('f5')
                    feedback_text = "PRESENTATION STARTED"
                    feedback_color = Theme.COLORS["primary"]
                else:
                    action = "Ignored (Already Running)"
            elif action_intent == "Next Slide":
                if ppt_active:
                    self.presentation_status = "Running"
                    self.current_slide = min(self.current_slide + 1, self.total_slides)
                    action = "Next Slide"
                    key_sent = "pagedown"
                    pyautogui.press('pagedown')
                    feedback_text = "NEXT SLIDE EXECUTED"
                    feedback_color = Theme.COLORS["primary"]
                else:
                    action = "Failed (No PPT)"
                    feedback_text = "NO ACTIVE PRESENTATION"
                    feedback_color = Theme.COLORS["error"]
            elif action_intent == "Prev Slide":
                if not ppt_active:
                    action = "Failed (No PPT)"
                    feedback_text = "NO ACTIVE PRESENTATION"
                    feedback_color = Theme.COLORS["error"]
                else:
                    self.presentation_status = "Running"
                    self.current_slide = max(self.current_slide - 1, 1)
                    action = "Prev Slide"
                    key_sent = "pageup"
                    pyautogui.press('pageup')
                    feedback_text = "PREVIOUS SLIDE EXECUTED"
                    feedback_color = Theme.COLORS["primary"]
            elif action_intent == "Pause Presentation":
                self.presentation_status = "Paused"
                action = "Paused"
                feedback_text = "PRESENTATION PAUSED"
                feedback_color = Theme.COLORS["warning"]
            elif action_intent == "End Presentation":
                self.presentation_status = "Stopped"
                feedback_text = "PRESENTATION ENDED"
                feedback_color = Theme.COLORS["error"]
                if not ppt_active:
                    action = "Stopped (No PPT)"
                else:
                    action = "Stopped"
                    key_sent = "esc"
                    pyautogui.press('esc')
                    
            if action != "None" and "Failed" not in action and "Ignored" not in action:
                if not manual:
                    cooldown = self.settings.get("cooldown_duration", 1.25)
                    self.cooldown_end_time = current_time + cooldown
                self.successful_commands += 1
                # Write to CSV log
                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                self.csv_writer.writerow([
                    ts,
                    gesture.upper(),
                    f"{confidence:.2%}",
                    action,
                    self.current_slide
                ])
                self.csv_file.flush()
                
                # Append to memory structures
                self.session_history_log.append((self.session_duration, gesture.upper(), confidence, "Success"))
                self.gesture_counts_total[gesture.upper()] = self.gesture_counts_total.get(gesture.upper(), 0) + 1
                
            print(f"[DEBUG] Action Selected: {action}")
            print(f"[DEBUG] Key Sent: {key_sent}")
            print(f"[DEBUG] Result: {feedback_text or action}")
            if feedback_text:
                self._show_feedback(feedback_text, feedback_color)
                
        else:
            mapping = self.settings.get("gesture_mappings", {})
            action_intent = mapping.get(gesture, "None")
            if action_intent != "None":
                action = "Ignored (Cooldown)"
                self.rejected_commands += 1
                print(f"[DEBUG] Action Selected: Ignored")
                print(f"[DEBUG] Result: ACTION BLOCKED BY COOLDOWN")
                self._show_feedback("ACTION BLOCKED BY COOLDOWN", Theme.COLORS["warning"])
                self.session_history_log.append((self.session_duration, gesture.upper(), confidence, "Rejected"))
                self.gesture_counts_total[gesture.upper()] = self.gesture_counts_total.get(gesture.upper(), 0) + 1
            
        if action != "None":
            # Update History UI
            time_str = time.strftime("%H:%M:%S")
            conf_str = f"{confidence:.0%}" if not manual else "100%"
            history_str = f"[{time_str}] {gesture.upper()} ({conf_str}) -> {action}"
            self.gesture_history_data.insert(0, history_str)
            if len(self.gesture_history_data) > 5:
                self.gesture_history_data.pop()
                
            for i, h_text in enumerate(self.gesture_history_data):
                self.history_entries[i].configure(text=h_text)
        
    def on_closing(self):
        """Cleanup logic when the window is closed."""
        print("Exiting application...")
        try:
            self.csv_file.close()
        except Exception:
            pass
            
        if hasattr(self, 'recognizer') and self.recognizer:
            self.recognizer.stop()
            
        # Force terminate to prevent Tkinter 'invalid command name' teardown errors
        import os
        os._exit(0)
