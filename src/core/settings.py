import os
import json

class SettingsManager:
    def __init__(self, settings_file="settings.json"):
        # Project root relative to src/core/settings.py
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.settings_path = os.path.join(project_root, settings_file)
        
        self.default_settings = {
            "confidence_threshold": 0.70,
            "cooldown_duration": 1.25,
            "webcam_index": 0,
            "theme": "dark",
            "gesture_mappings": {
                "fist": "Prev Slide",
                "like": "Next Slide",
                "peace": "End Presentation",
                "stop": "Pause Presentation",
                "palm": "None"
            }
        }
        
        self.settings = self._load_settings()

    def _load_settings(self):
        """Loads settings from JSON or creates default if missing."""
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Merge with defaults to ensure missing keys are populated
                    merged = self.default_settings.copy()
                    
                    for k, v in data.items():
                        if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
                            merged[k].update(v)
                        else:
                            merged[k] = v
                            
                    return merged
            except Exception as e:
                print(f"[SettingsManager] Error reading JSON: {e}. Reverting to defaults.")
                return self.default_settings.copy()
        else:
            self._save_settings(self.default_settings)
            return self.default_settings.copy()

    def _save_settings(self, data=None):
        """Saves current settings to JSON file."""
        if data is None:
            data = self.settings
            
        with open(self.settings_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def get(self, key, default=None):
        """Retrieve a specific setting."""
        return self.settings.get(key, default)

    def update(self, key, value):
        """Update a specific setting and save to disk."""
        self.settings[key] = value
        self._save_settings()

    def update_multiple(self, updates_dict):
        """Update multiple settings at once and save to disk."""
        for k, v in updates_dict.items():
            self.settings[k] = v
        self._save_settings()
