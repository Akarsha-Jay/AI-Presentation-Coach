"""
theme.py

Centralized Design System for the AI Presentation Coach.
Contains color palettes, typography rules, and spatial metrics.
"""

import customtkinter as ctk

class Theme:
    # --- Color Palette ---
    # CustomTkinter automatically uses the first color for light mode and the second for dark mode.
    COLORS = {
        "bg_base": ("#F5F7FA", "#0B0F19"),       
        "bg_surface": ("#FFFFFF", "#1E1E1E"),    
        "bg_surface_hover": ("#E2E8F0", "#2A2A2A"),
        "primary": ("#00A078", "#00C896"),       
        "primary_hover": ("#008060", "#00A078"),
        "warning": ("#F59E0B", "#FFB020"),
        "error": ("#EF4444", "#FF5252"),
        "text_main": ("#0F172A", "#FFFFFF"),
        "text_sub": ("#64748B", "#A0A0A0"),
        "border": ("#CBD5E1", "#333333")
    }

    # --- Metrics ---
    METRICS = {
        "corner_radius": 12,
        "padding_small": 10,
        "padding_medium": 20,
        "padding_large": 30
    }

    # --- Typography ---
    # We define factory methods because CTkFont requires an initialized root window.
    @staticmethod
    def font_h1():
        return ctk.CTkFont(family="Segoe UI", size=28, weight="bold")
        
    @staticmethod
    def font_h2():
        return ctk.CTkFont(family="Segoe UI", size=20, weight="bold")
        
    @staticmethod
    def font_h3():
        return ctk.CTkFont(family="Segoe UI", size=16, weight="bold")
        
    @staticmethod
    def font_body():
        return ctk.CTkFont(family="Segoe UI", size=14)
        
    @staticmethod
    def font_body_small():
        return ctk.CTkFont(family="Segoe UI", size=12)
        
    @staticmethod
    def font_value():
        return ctk.CTkFont(family="Segoe UI", size=36, weight="bold")
        
    @staticmethod
    def font_icon(size=24):
        # Segoe Fluent Icons or Segoe UI Symbol
        return ctk.CTkFont(family="Segoe Fluent Icons", size=size)
