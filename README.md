# AI-Powered Presentation & Interview Coach

An advanced AI-powered application designed to serve as a presentation and interview coach. Using computer vision and deep learning techniques, this tool analyzes body language, hand gestures, facial expressions, and more to provide actionable feedback for improving presentation skills.

## Project Structure

- `app/`: Streamlit web application.
- `assets/`: Images, logos, and other static assets.
- `data/`: Datasets used for training and testing.
- `model/`: Trained machine learning models (e.g., Keras/TensorFlow files).
- `notebooks/`: Jupyter notebooks for data exploration, model training, and experimentation.
- `reports/`: Generated analysis reports and figures.
- `src/`: Core source code including model definitions, data processing scripts, and utilities.

## Requirements

The project relies on several key libraries including TensorFlow, OpenCV, NumPy, Pandas, Matplotlib, Streamlit, and Plotly. 

To install the required dependencies, run:

```bash
pip install -r requirements.txt
```

## Setup

1. Clone this repository.
2. Create a virtual environment (`venv` or `conda`).
3. Install the required dependencies.
4. Run the Streamlit application:

```bash
streamlit run app/main.py
```

## Features
- Real-time video analysis
- Hand gesture recognition
- Posture and expression tracking
- Interactive dashboard for feedback
