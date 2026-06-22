import tensorflow as tf
import os

model_path = r"d:\Projects\AI-Presentation-Coach\model\presentation_gesture_model.keras"
if os.path.exists(model_path):
    print("Loading model...")
    model = tf.keras.models.load_model(model_path)
    print("Model loaded.")
    print("Inputs:", model.inputs)
    print("Outputs:", model.outputs)
    
    # Try to find class names in metadata if possible
    # In newer Keras, sometimes it's saved in the config or as an attribute
    if hasattr(model, 'class_names'):
        print("class_names:", model.class_names)
    else:
        print("No class_names attribute found on model directly.")
        
    print("Config:", model.get_config())
else:
    print("Model not found")
