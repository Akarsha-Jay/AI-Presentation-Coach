"""
config.py

Configuration parameters and shared variables for the AI Presentation Coach.
"""

# Gesture class labels that the model was trained to predict.
# Ensure the order matches the output classes of the trained model.
GESTURE_LABELS = [
    "fist",
    "like",
    "palm",
    "peace",
    "stop"
]

# Model input parameters
MODEL_INPUT_SIZE = (224, 224)
CONFIDENCE_THRESHOLD = 0.70
