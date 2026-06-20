import os
import tensorflow as tf
from config import GESTURE_LABELS

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    model_path = os.path.join(project_root, "model", "presentation_gesture_model.keras")
    
    try:
        model = tf.keras.models.load_model(model_path)
    except Exception as e:
        print(f"Error loading model from {model_path}: {e}")
        return

    output_shape = model.output_shape
    num_classes = output_shape[-1]
    num_labels = len(GESTURE_LABELS)

    print(f"Model output shape: {output_shape}")
    print(f"Number of output classes: {num_classes}")
    print(f"Number of gesture labels: {num_labels}")

    if num_labels == num_classes:
        print("\nLabels verified successfully")
    else:
        raise ValueError(f"Mismatch: Model has {num_classes} output classes, but {num_labels} labels are defined in config.py")

if __name__ == "__main__":
    main()
