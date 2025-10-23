# YOLOv8 Object Detection and Tracking Web Application

## Project Overview
A real-time object detection and tracking web application built with Streamlit and YOLOv8. The application allows users to detect and track objects in images, videos, webcam streams, RTSP streams, and YouTube videos.

## Technology Stack
- **Framework**: Streamlit (Python web framework)
- **ML Model**: YOLOv8 (object detection and segmentation)
- **Deep Learning**: PyTorch, torchvision
- **Computer Vision**: OpenCV (cv2)
- **Video Processing**: yt-dlp for YouTube support
- **Python**: 3.11

## Project Structure
```
.
├── app.py                 # Main Streamlit application
├── helper.py             # Helper functions for video/image processing
├── settings.py           # Configuration and paths
├── requirements.txt      # Python dependencies
├── packages.txt          # System dependencies
├── .streamlit/          
│   └── config.toml       # Streamlit server configuration
├── weights/              # YOLOv8 model weights
│   ├── yolov8n.pt       # Detection model
│   ├── yolov8n-seg.pt   # Segmentation model
│   └── yolov8n-cls.pt   # Classification model
├── images/               # Sample images and results
├── videos/               # Sample videos for processing
└── assets/               # Demo assets
```

## Features
1. **Detection Modes**:
   - Object Detection
   - Instance Segmentation

2. **Input Sources**:
   - Static images (upload or use defaults)
   - Pre-loaded videos
   - Webcam (live stream)
   - RTSP streams
   - YouTube videos

3. **Configurable Parameters**:
   - Model confidence threshold (25-100%)
   - Optional object tracking
   - Multiple tracker options (bytetrack.yaml, botsort.yaml)

## Setup Information

### System Dependencies
- Python 3.11 (installed via Replit modules)
- All Python packages installed via pip with CPU-only PyTorch for space efficiency

### Development Server
- **Host**: 0.0.0.0
- **Port**: 5000
- **CORS**: Disabled for Replit proxy compatibility
- **XSRF Protection**: Disabled for development

### Deployment Configuration
- **Type**: Autoscale (stateless web application)
- **Run Command**: `streamlit run app.py --server.port=5000 --server.address=0.0.0.0`

## Recent Changes
- **2025-10-23**: Replit environment setup completed
  - Installed Python 3.11 module
  - Installed CPU-only PyTorch (2.3.1+cpu) to save disk space (~190MB vs ~900MB CUDA version)
  - Installed all required dependencies: streamlit, ultralytics, opencv-python-headless, yt-dlp, lap
  - Configured Streamlit to bind to 0.0.0.0:5000 with CORS and XSRF protection disabled for Replit proxy
  - Created .streamlit/config.toml with proper server settings
  - Set up workflow "Streamlit App" to run on port 5000
  - Configured deployment for autoscale deployment type
  - Created .gitignore for Python project
  - App is running successfully and serving HTTP responses

## Usage
The application automatically starts on port 5000. Access it through the Replit webview to:
1. Select task type (Detection or Segmentation)
2. Adjust model confidence threshold
3. Choose input source
4. Upload media or use pre-loaded samples
5. Click "Detect Objects" to run inference

## Pre-trained Models
The project includes pre-trained YOLOv8 nano models:
- Detection: `yolov8n.pt`
- Segmentation: `yolov8n-seg.pt`
- Classification: `yolov8n-cls.pt`

## Notes
- GPU acceleration is available if CUDA-compatible GPU is present
- Video processing may be slower without GPU
- YouTube video processing requires stable internet connection
- Large model files (weights/*.pt) are tracked in git as they're essential for the app
