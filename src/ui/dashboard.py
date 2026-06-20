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
        
        self.gesture_history_data = []
        
        # Performance tracking counters
        self.successful_commands = 0
        self.rejected_commands = 0
        self.frame_times = []
        self.fps_frame_times = []
        
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
            if confidence >= CONFIDENCE_THRESHOLD:
                current_label_upper = label.upper()
                if current_label_upper == self.candidate_gesture:
                    self.consecutive_frames += 1
                else:
                    self.candidate_gesture = current_label_upper
                    self.consecutive_frames = 1
                
                # Action lock-in on 5 consecutive frames
                if self.consecutive_frames >= 5 and self.candidate_gesture != self.locked_gesture:
                    # VALID GESTURE ACCEPTED: Update average confidence
                    self.confidences.append(confidence)
                    if len(self.confidences) > 100:
                        self.confidences.pop(0)
                    avg_conf = sum(self.confidences) / len(self.confidences)
                    self.labels["Average Confidence"].configure(text=f"{avg_conf:.0%}")
                    
                    if self.locked_gesture != "--":
                        self.total_gestures_detected += 1
                        self.last_detected_gesture = self.locked_gesture
                    
                    self.locked_gesture = self.candidate_gesture
                    
                    gesture = label.lower()
                    action = "None"
                    
                    if not is_cooldown:
                        if gesture == "like":
                            if self.presentation_status in ["Waiting", "Stopped"]:
                                self.presentation_status = "Running"
                                action = "Started"
                                pyautogui.press('f5')
                            else:
                                self.presentation_status = "Running"
                                self.current_slide = min(self.current_slide + 1, self.total_slides)
                                action = "Next Slide"
                                pyautogui.press('space')
                        elif gesture == "fist":
                            self.presentation_status = "Running"
                            self.current_slide = max(self.current_slide - 1, 1)
                            action = "Prev Slide"
                            pyautogui.press('left')
                        elif gesture == "stop":
                            self.presentation_status = "Paused"
                            action = "Paused"
                        elif gesture == "peace":
                            self.presentation_status = "Stopped"
                            action = "Stopped"
                            pyautogui.press('esc')
                            
                        if action != "None" and action != "Ignored (Cooldown)":
                            self.cooldown_end_time = current_time + 2.0
                            self.successful_commands += 1
                            # Write to CSV log
                            ts = time.strftime("%Y-%m-%d %H:%M:%S")
                            self.csv_writer.writerow([
                                ts,
                                self.locked_gesture,
                                f"{confidence:.2%}",
                                action,
                                self.current_slide
                            ])
                            self.csv_file.flush()
                    else:
                        if gesture in ["like", "fist", "stop", "peace"]:
                            action = "Ignored (Cooldown)"
                            self.rejected_commands += 1
                        
                    # Update History UI
                    time_str = time.strftime("%H:%M:%S")
                    conf_str = f"{confidence:.0%}"
                    history_str = f"[{time_str}] {self.locked_gesture} ({conf_str}) -> {action}"
                    self.gesture_history_data.insert(0, history_str)
                    if len(self.gesture_history_data) > 5:
                        self.gesture_history_data.pop()
                        
                    for i, h_text in enumerate(self.gesture_history_data):
                        self.history_entries[i].configure(text=h_text)
                        
                self.labels["Current Gesture"].configure(text=self.locked_gesture)
                display_text = f"{label.upper()}: {confidence:.0%} (Live)"
            else:
                self.candidate_gesture = None
                self.consecutive_frames = 0
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
        
    def on_closing(self):
        """Cleanup logic when the window is closed."""
        print("Exiting application...")
        self.csv_file.close()
        self.recognizer.stop()
        self.destroy()
