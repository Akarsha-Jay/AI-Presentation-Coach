import os
import re

file_path = r"d:\Projects\AI-Presentation-Coach\src\ui\dashboard.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

replacements = [
    (r'fg_color="#1E1E1E"', r'fg_color=Theme.COLORS["bg_surface"]'),
    (r'text_color="#A0A0A0"', r'text_color=Theme.COLORS["text_sub"]'),
    (r'text_color="white"', r'text_color=Theme.COLORS["text_main"]'),
    (r'fg_color="#2A2A2A"', r'fg_color=Theme.COLORS["bg_surface_hover"]'),
    (r'color="#00C896"', r'color=Theme.COLORS["primary"]'),
    (r'color="#FFB020"', r'color=Theme.COLORS["warning"]'),
    (r'color="#FF5252"', r'color=Theme.COLORS["error"]'),
    (r'text_color="#555555"', r'text_color=Theme.COLORS["text_sub"]'),
    (r'fg_color="#00C896"', r'fg_color=Theme.COLORS["primary"]'),
    (r'hover_color="#00A078"', r'hover_color=Theme.COLORS["primary_hover"]'),
    (r'text_color="#00C896"', r'text_color=Theme.COLORS["primary"]'),
    (r'fg_color="#2B2B2B"', r'fg_color=Theme.COLORS["bg_surface_hover"]'),
    (r'hover_color="#3B3B3B"', r'hover_color=Theme.COLORS["border"]'),
    (r'fg_color="#FF5252"', r'fg_color=Theme.COLORS["error"]'),
    (r'hover_color="#D32F2F"', r'hover_color=Theme.COLORS["error"]'),
    (r'text_color="#B0B0B0"', r'text_color=Theme.COLORS["text_sub"]'),
    (r'fg_color="#0A0A0A"', r'fg_color=Theme.COLORS["bg_base"]'),
    
    (r'bg="#1E1E1E"', r'bg=Theme.COLORS["bg_surface"][1]'),
    (r'outline="#333333"', r'outline=Theme.COLORS["border"][1]'),
    (r'fill="white"', r'fill=Theme.COLORS["text_main"][1]'),
    
    (r'status_color = "#00C896"', r'status_color = Theme.COLORS["primary"]'),
    (r'status_color = "#FFB020"', r'status_color = Theme.COLORS["warning"]'),
    (r'status_color = "#FF5252"', r'status_color = Theme.COLORS["error"]'),
    
    (r'feedback_color = "#00C896"', r'feedback_color = Theme.COLORS["primary"]'),
    (r'feedback_color = "#FF5252"', r'feedback_color = Theme.COLORS["error"]'),
    (r'feedback_color = "#FFB020"', r'feedback_color = Theme.COLORS["warning"]'),
    
    (r'self._show_feedback("SETTINGS SAVED!", "#00C896")', r'self._show_feedback("SETTINGS SAVED!", Theme.COLORS["primary"])'),
    (r'self._show_feedback("ACTION BLOCKED BY COOLDOWN", "#FFB020")', r'self._show_feedback("ACTION BLOCKED BY COOLDOWN", Theme.COLORS["warning"])'),
    
    (r'color="white"', r'color=Theme.COLORS["text_main"]'),
    (r'text_color="white"', r'text_color=Theme.COLORS["text_main"]'),
]

for old, new in replacements:
    content = content.replace(old, new)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Colors replaced in dashboard.py")
