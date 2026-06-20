import os
import sys

# Suppress basic TensorFlow info logs to keep the console clean
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

try:
    import tensorflow as tf
except ImportError:
    print("Error: TensorFlow is not installed. Please run: pip install -r requirements.txt")
    sys.exit(1)

def test_model_loading():
    # Construct the absolute path to the model relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    model_path = os.path.join(project_root, 'model', 'presentation_gesture_model.keras')

    print(f"Attempting to load model from:\n{model_path}\n")
    
    if not os.path.exists(model_path):
        print(f"Error: Model file not found at {model_path}")
        return

    try:
        # Load the model
        model = tf.keras.models.load_model(model_path)
        
        print("--- Model Loaded Successfully ---")
        print(f"Model Name:       {model.name}")
        print(f"Input Shape:      {model.input_shape}")
        print(f"Output Shape:     {model.output_shape}")
        print(f"Total Parameters: {model.count_params():,}")
        print("---------------------------------")
        
    except Exception as e:
        print(f"Error: Failed to load the model.")
        print(f"Exception details: {str(e)}")

if __name__ == "__main__":
    test_model_loading()
