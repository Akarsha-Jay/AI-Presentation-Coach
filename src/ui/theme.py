"""
theme.py

Centralized Design System for the AI Presentation Coach.
Contains color palettes, typography rules, and spatial metrics.
"""

import customtkinter as ctk

class Theme:
    # --- Color Palette ---
    COLORS = {
        "bg_base": "#0B0F19",       # Deep, dark background
        "bg_surface": "#151A28",    # Elevated surface (Cards/Sidebar)
        "bg_surface_hover": "#1F263B",
        "primary": "#00C896",       # Emerald Accent
        "primary_hover": "#00A078",
        "warning": "#FFB020",
        "error": "#FF5252",
        "text_main": "#FFFFFF",
        "text_sub": "#8F9BB3",
        "border": "#2E3A59"
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
