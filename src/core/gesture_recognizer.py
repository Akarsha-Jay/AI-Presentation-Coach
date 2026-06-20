"""
Gesture Recognizer Module

Handles the background webcam capture and EfficientNet model inference thread.
Runs continuously to decouple Heavy TensorFlow predictions from the UI event loop.
"""

import os
import sys
import cv2
import time
import threading
import numpy as np

# Suppress basic TensorFlow logs to keep console output clean
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

try:
    import tensorflow as tf
    from tensorflow.keras.applications.efficientnet import preprocess_input
except ImportError:
    print("Error: TensorFlow is not installed. Please run: pip install -r requirements.txt")
    sys.exit(1)

# Import config (we are now in src/core, so config is in the parent directory)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GESTURE_LABELS, MODEL_INPUT_SIZE

class GestureRecognizer:
    """
    Background worker class that initializes the webcam and Keras model,
    then continuously loops on a separate thread reading frames and producing predictions.
    """
    def __init__(self):
        self.model = self._load_model()
        
        print("Initializing webcam...")
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("Error: Could not open the webcam.")
            sys.exit(1)
            
        self.lock = threading.Lock()
        
        # State variables to share safely with the UI
        self.latest_frame = None
        self.latest_prediction = None
        self.latest_inference_ms = 0.0
        self.is_running = False
        
        # Performance trackers
        self.total_predictions = 0
        
    def _load_model(self):
        """Loads the trained Keras model from the project's model/ directory."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(script_dir))
        model_path = os.path.join(project_root, 'model', 'presentation_gesture_model.keras')

        if not os.path.exists(model_path):
            print(f"Error: Model not found at {model_path}")
            sys.exit(1)

        print(f"Loading model from {model_path}...")
        try:
            model = tf.keras.models.load_model(model_path)
            print("Model loaded successfully.")
            return model
        except Exception as e:
            print(f"Error loading model: {e}")
            sys.exit(1)

    def preprocess_frame(self, frame):
        """
        Preprocesses a raw webcam frame for the EfficientNet model.
        Resizes and applies the built-in EfficientNet scaling.
        """
        resized_frame = cv2.resize(frame, MODEL_INPUT_SIZE)
        rgb_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
        input_array = np.array(rgb_frame, dtype=np.float32)
        input_batch = np.expand_dims(input_array, axis=0)
        return preprocess_input(input_batch)

    def start(self):
        """Starts the background video and inference thread."""
        self.is_running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        """
        Continuously reads from the webcam, runs preprocessing and prediction,
        and saves the outputs for the UI thread to fetch.
        """
        while self.is_running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.01)
                continue
                
            # Flip the frame horizontally for a more natural "mirror" view
            frame = cv2.flip(frame, 1)
            
            # Preprocess and infer – time it
            t_pred_start = time.perf_counter()
            input_tensor = self.preprocess_frame(frame)
            predictions = self.model.predict(input_tensor, verbose=0)[0]
            t_pred_end = time.perf_counter()
            proc_ms = (t_pred_end - t_pred_start) * 1000
            
            # Acquire lock and safely update state
            with self.lock:
                self.latest_frame = frame.copy()
                self.latest_prediction = predictions
                self.latest_inference_ms = proc_ms
                self.total_predictions += 1
            
            # Sleep slightly to prevent 100% CPU lock if inference is extremely fast
            time.sleep(0.005)

    def get_latest_data(self):
        """Returns a snapshot of the latest frame, prediction array, and inference time."""
        with self.lock:
            if self.latest_frame is None:
                return None, None, 0.0
            return self.latest_frame.copy(), self.latest_prediction.copy(), self.latest_inference_ms

    def stop(self):
        """Stops the loop and releases the webcam."""
        self.is_running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=2.0)
        if self.cap and self.cap.isOpened():
            self.cap.release()
