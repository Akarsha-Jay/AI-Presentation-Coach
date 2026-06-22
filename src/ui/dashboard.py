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
from PIL import Image, ImageTk

if sys.platform == "win32":
    import ctypes

# Import config (we are now in src/ui, so config is in the parent directory)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GESTURE_LABELS, CONFIDENCE_THRESHOLD

class DashboardApp(ctk.CTk):
    """Main Dashboard Window using CustomTkinter."""
    
    def __init__(self, recognizer):
        super().__init__()
        
        self.recognizer = recognizer
        self.title("AI Presentation Coach Dashboard")
        self.geometry("1600x750")
        
        # Grid layout
        self.grid_columnconfigure(0, weight=3) # Webcam
        self.grid_columnconfigure(1, weight=1) # Statistics Panel
        self.grid_columnconfigure(2, weight=1) # History
        self.grid_rowconfigure(0, weight=1)
        
        self._setup_ui()
        self._init_state()
        self._setup_logging()
        
        # Start GUI update loop (runs on main thread)
        self.update_frame()
        
    def _setup_ui(self):
        """Initializes all GUI frames and labels."""
        # 1. Webcam Frame
        self.video_frame = ctk.CTkFrame(self)
        self.video_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.video_label = ctk.CTkLabel(self.video_frame, text="")
        self.video_label.pack(expand=True, fill="both", padx=10, pady=10)
        
        self.feedback_label = ctk.CTkLabel(self.video_frame, text="", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"), text_color="yellow")
        self.feedback_label.pack(pady=(0, 10))
        
        # 2. Statistics Panel
        self.stats_frame = ctk.CTkFrame(self)
        self.stats_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.stats_label_title = ctk.CTkLabel(self.stats_frame, text="Real-Time Statistics", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"))
        self.stats_label_title.pack(pady=(20, 30))
        
        self.labels = {}
        stat_fields = [
            ("🖐️", "Current Gesture"),
            ("🎯", "Confidence"),
            ("🎬", "Presentation Status"),
            ("⏱️", "Presentation Timer"),
            ("✅", "Total Commands Executed"),
            ("📈", "Average Confidence"),
            ("⚡", "Current FPS"),
            ("⏱️", "Model Inference Time")
        ]
        
        for icon, field in stat_fields:
            frame = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
            frame.pack(fill="x", padx=20, pady=8)
            title = ctk.CTkLabel(frame, text=f"{icon}  {field}:", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"))
            title.pack(anchor="w")
            value = ctk.CTkLabel(frame, text="--", font=ctk.CTkFont(family="Segoe UI", size=18))
            value.pack(anchor="w")
            self.labels[field] = value
            
            if field == "Confidence":
                self.confidence_progress = ctk.CTkProgressBar(frame)
                self.confidence_progress.pack(fill="x", pady=(5, 0))
                self.confidence_progress.set(0)
                
        # 3. History Panel
        self.history_frame = ctk.CTkFrame(self)
        self.history_frame.grid(row=0, column=2, padx=20, pady=20, sticky="nsew")
        self.history_label_title = ctk.CTkLabel(self.history_frame, text="Recent History", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"))
        self.history_label_title.pack(pady=(20, 30))
        
        self.history_entries = []
        for i in range(5):
            entry = ctk.CTkLabel(self.history_frame, text="-", font=ctk.CTkFont(family="Segoe UI", size=14))
            entry.pack(anchor="w", padx=20, pady=10)
            self.history_entries.append(entry)
            
        # 4. Test Controls Panel
        self.test_frame = ctk.CTkFrame(self)
        self.test_frame.grid(row=1, column=0, columnspan=3, padx=20, pady=10, sticky="ew")
        self.test_label = ctk.CTkLabel(self.test_frame, text="Test Controls:", font=ctk.CTkFont(family="Segoe UI", weight="bold"))
        self.test_label.pack(side="left", padx=20, pady=10)
        
        btn_prev = ctk.CTkButton(self.test_frame, text="Prev Slide (FIST)", command=lambda: self._execute_action("fist", manual=True))
        btn_prev.pack(side="left", padx=10, pady=10)
        
        btn_next = ctk.CTkButton(self.test_frame, text="Next Slide (LIKE)", command=lambda: self._execute_action("like", manual=True))
        btn_next.pack(side="left", padx=10, pady=10)

    def _init_state(self):
        """Initializes application state tracking variables."""
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
        
        # Performance tracking counters
        self.successful_commands = 0
        self.rejected_commands = 0
        self.frame_times = []
        self.fps_frame_times = []
        self._feedback_timer = None
        
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
        """Attempts to find and focus a PowerPoint Slide Show window.
        Returns True if Slide Show is found and active.
        If Slide Show is not found but main PowerPoint window is, focuses that and returns False.
        """
        if sys.platform == "win32":
            # 1. Try finding Slide Show
            hwnd = ctypes.windll.user32.FindWindowW("screenClass", None)
            if hwnd and ctypes.windll.user32.IsWindowVisible(hwnd):
                ctypes.windll.user32.ShowWindow(hwnd, 9)
                self._force_foreground(hwnd)
                return True
            
            # 2. Try finding PowerPoint Edit Window
            hwnd_edit = ctypes.windll.user32.FindWindowW("PPTFrameClass", None)
            if hwnd_edit and ctypes.windll.user32.IsWindowVisible(hwnd_edit):
                ctypes.windll.user32.ShowWindow(hwnd_edit, 9)
                self._force_foreground(hwnd_edit)
                return False
                
        return False
        
    def _show_feedback(self, text, color="yellow"):
        """Displays feedback on the dashboard and clears it after 3 seconds."""
        self.feedback_label.configure(text=text, text_color=color)
        if self._feedback_timer:
            self.after_cancel(self._feedback_timer)
        self._feedback_timer = self.after(3000, lambda: self.feedback_label.configure(text=""))

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

    def update_frame(self):
        """
        Periodic GUI loop called via Tkinter's `after()`.
        Fetches the latest data from the background thread and redraws the UI.
        """
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
                
            self.labels["Current FPS"].configure(text=str(fps))
            self.labels["Model Inference Time"].configure(text=f"{avg_proc:.1f} ms")
            self.labels["Total Commands Executed"].configure(text=str(self.successful_commands))
            
            # --- State and stabilization logic ---
            current_label_upper = label.upper() if confidence >= CONFIDENCE_THRESHOLD else "NONE"
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
                        self.labels["Average Confidence"].configure(text=f"{avg_conf:.0%}")
                        
                        self._execute_action(self.locked_gesture.lower(), confidence=confidence, manual=False)
                    
            if self.locked_gesture != "NONE" and self.locked_gesture != "--":
                self.labels["Current Gesture"].configure(text=self.locked_gesture)
                display_text = f"{label.upper()}: {confidence:.0%} (Live)"
            else:
                self.labels["Current Gesture"].configure(text="UNKNOWN GESTURE")
                display_text = f"UNKNOWN: {confidence:.0%} (Live)"
                
            # --- Global Label Colors ---
            status_color = "white"
            if self.presentation_status == "Running":
                status_color = "#2ECC71" # Green
            elif self.presentation_status == "Paused":
                status_color = "#F39C12" # Orange
            elif self.presentation_status == "Stopped":
                status_color = "#E74C3C" # Red
                
            self.labels["Confidence"].configure(text=f"{confidence:.0%}")
            self.confidence_progress.set(confidence)
            self.labels["Presentation Status"].configure(text=self.presentation_status, text_color=status_color)
            self.labels["Presentation Timer"].configure(text=duration_str)
            
            # --- Draw UI on Video Frame ---
            cv2.putText(
                img=frame,
                text=display_text,
                org=(20, 50),
                fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                fontScale=1.0,
                color=(0, 255, 0),
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
            ppt_active = self._focus_powerpoint()
            time.sleep(0.1) # Small delay to ensure focus is applied
            active_win = self._get_active_window_title()
            print(f"[DEBUG] Active Window: {active_win}")
            
            if gesture == "like":
                if not ppt_active:
                    self.presentation_status = "Running"
                    action = "Started"
                    key_sent = "f5"
                    pyautogui.press('f5')
                    feedback_text = "PRESENTATION STARTED"
                    feedback_color = "#2ECC71"
                else:
                    self.presentation_status = "Running"
                    self.current_slide = min(self.current_slide + 1, self.total_slides)
                    action = "Next Slide"
                    key_sent = "pagedown"
                    pyautogui.press('pagedown')
                    feedback_text = "NEXT SLIDE EXECUTED"
                    feedback_color = "#2ECC71"
            elif gesture == "fist":
                if not ppt_active:
                    action = "Failed (No PPT)"
                    feedback_text = "NO ACTIVE PRESENTATION"
                    feedback_color = "red"
                else:
                    self.presentation_status = "Running"
                    self.current_slide = max(self.current_slide - 1, 1)
                    action = "Prev Slide"
                    key_sent = "pageup"
                    pyautogui.press('pageup')
                    feedback_text = "PREVIOUS SLIDE EXECUTED"
                    feedback_color = "#2ECC71"
            elif gesture == "stop":
                self.presentation_status = "Paused"
                action = "Paused"
                feedback_text = "PRESENTATION PAUSED"
                feedback_color = "#F39C12"
            elif gesture == "peace":
                if not ppt_active:
                    action = "Failed (No PPT)"
                    feedback_text = "NO ACTIVE PRESENTATION"
                    feedback_color = "red"
                else:
                    self.presentation_status = "Stopped"
                    action = "Stopped"
                    key_sent = "esc"
                    pyautogui.press('esc')
                    feedback_text = "PRESENTATION ENDED"
                    feedback_color = "#E74C3C"
                    
            if action != "None" and "Failed" not in action:
                if not manual:
                    self.cooldown_end_time = current_time + 1.25
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
                
            print(f"[DEBUG] Action Selected: {action}")
            print(f"[DEBUG] Key Sent: {key_sent}")
            print(f"[DEBUG] Result: {feedback_text or action}")
            if feedback_text:
                self._show_feedback(feedback_text, feedback_color)
                
        else:
            if gesture in ["like", "fist", "stop", "peace"]:
                action = "Ignored (Cooldown)"
                self.rejected_commands += 1
                print(f"[DEBUG] Action Selected: Ignored")
                print(f"[DEBUG] Result: ACTION BLOCKED BY COOLDOWN")
                self._show_feedback("ACTION BLOCKED BY COOLDOWN", "orange")
            
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
        self.csv_file.close()
        self.recognizer.stop()
        self.destroy()
