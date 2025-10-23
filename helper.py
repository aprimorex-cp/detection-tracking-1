from ultralytics import YOLO
import streamlit as st
import cv2
import torch
import settings
from cap_from_youtube import cap_from_youtube


def load_model(model_path):
    """
    Loads a YOLO object detection model from the specified model_path.

    Parameters:
        model_path (str): The path to the YOLO model file.

    Returns:
        A YOLO object detection model.
    """
    # For PyTorch 2.6+, we need to load with weights_only=False
    # This is safe because we trust the YOLOv8 model source
    # The ultralytics library handles the torch.load internally,
    # so we need to monkey-patch it temporarily
    import functools
    original_load = torch.load

    # Create a wrapper that uses weights_only=False
    def patched_load(*args, **kwargs):
        kwargs['weights_only'] = False
        return original_load(*args, **kwargs)

    # Temporarily replace torch.load
    torch.load = patched_load

    try:
        model = YOLO(model_path)
    finally:
        # Restore original torch.load
        torch.load = original_load

    return model


def display_tracker_options():
    display_tracker = st.radio("Display Tracker", ('Yes', 'No'))
    is_display_tracker = True if display_tracker == 'Yes' else False
    if is_display_tracker:
        tracker_type = st.radio("Tracker", ("bytetrack.yaml", "botsort.yaml"))
        return is_display_tracker, tracker_type
    return is_display_tracker, None


def _display_detected_frames(conf, model, st_frame, image, is_display_tracking=None, tracker=None):
    """
    Display the detected objects on a video frame using the YOLOv8 model.

    Args:
    - conf (float): Confidence threshold for object detection.
    - model (YoloV8): A YOLOv8 object detection model.
    - st_frame (Streamlit object): A Streamlit object to display the detected video.
    - image (numpy array): A numpy array representing the video frame.
    - is_display_tracking (bool): A flag indicating whether to display object tracking (default=None).

    Returns:
    None
    """

    # Resize the image to a standard size
    image = cv2.resize(image, (720, int(720*(9/16))))

    # Display object tracking, if specified
    if is_display_tracking:
        res = model.track(image, conf=conf, persist=True, tracker=tracker)
    else:
        # Predict the objects in the image using the YOLOv8 model
        res = model.predict(image, conf=conf)

    # # Plot the detected objects on the video frame
    res_plotted = res[0].plot()
    st_frame.image(res_plotted,
                   caption='Detected Video',
                   channels="BGR",
                   use_column_width=True
                   )


# Note: get_youtube_stream_url() function has been removed
# We now use cap_from_youtube library which handles YouTube URL extraction
# and returns a cv2.VideoCapture object directly, avoiding OpenCV's issues
# with long YouTube URLs.


def play_youtube_video(conf, model):
    """
    Plays a YouTube video stream with object detection and optional tracking.

    Uses cap_from_youtube library to reliably extract and open YouTube video streams,
    which handles the complexity of YouTube's video delivery system.

    Parameters:
        conf (float): Confidence threshold for YOLOv8 model.
        model: An instance of the YOLOv8 class containing the model.

    Returns:
        None
    """
    source_youtube = st.sidebar.text_input("YouTube Video url")
    is_display_tracker, tracker = display_tracker_options()

    if st.sidebar.button('Detect Objects'):
        if not source_youtube:
            st.sidebar.error("Please enter a YouTube URL")
            return

        # Validate YouTube URL format
        if not ('youtube.com/watch' in source_youtube or 'youtu.be/' in source_youtube):
            st.sidebar.error("Invalid YouTube URL. Please provide a valid YouTube video URL.")
            return

        vid_cap = None
        try:
            # Step 1: Open YouTube video using cap_from_youtube
            # This library handles YouTube URL extraction and returns a cv2.VideoCapture object
            st.sidebar.info("Extracting and opening YouTube video stream...")

            # Use 720p for optimal balance between quality and performance
            # Detection doesn't need 4K resolution
            vid_cap = cap_from_youtube(source_youtube, '720p')

            # Step 2: Verify stream opened successfully
            if not vid_cap or not vid_cap.isOpened():
                st.sidebar.error(
                    "Failed to open video stream. Possible causes:\n"
                    "- Video may be private, age-restricted, or removed\n"
                    "- Video may be region-blocked\n"
                    "- Network connectivity issues\n\n"
                    "Please try a different public video."
                )
                return

            # Get video properties for info
            fps = vid_cap.get(cv2.CAP_PROP_FPS)
            width = int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            st.sidebar.success(f"YouTube video opened successfully!")
            st.sidebar.info(f"Resolution: {width}x{height} | FPS: {fps:.1f}")

            # Step 3: Process video frames with detection/tracking
            st_frame = st.empty()
            frame_count = 0

            while vid_cap.isOpened():
                success, image = vid_cap.read()

                if success:
                    frame_count += 1
                    _display_detected_frames(
                        conf,
                        model,
                        st_frame,
                        image,
                        is_display_tracker,
                        tracker
                    )
                else:
                    # End of stream or read error
                    st.sidebar.info(f"Stream ended. Processed {frame_count} frames.")
                    break

        except Exception as e:
            # Detailed error reporting
            error_msg = str(e)

            # Provide helpful error messages based on the error type
            if "cap_from_youtube" in error_msg or "yt_dlp" in error_msg or "yt-dlp" in error_msg:
                st.sidebar.error(
                    f"YouTube Video Error:\n{error_msg}\n\n"
                    "Possible solutions:\n"
                    "- Ensure the video is public and available\n"
                    "- Check if the video is available in your region\n"
                    "- Try a different video\n"
                    "- Update dependencies: pip install --upgrade yt-dlp cap-from-youtube"
                )
            elif "timeout" in error_msg.lower() or "connection" in error_msg.lower():
                st.sidebar.error(
                    f"Network Error:\n{error_msg}\n\n"
                    "The connection timed out or was interrupted:\n"
                    "- Check your internet connection\n"
                    "- Try again in a moment\n"
                    "- Try a different video"
                )
            else:
                st.sidebar.error(
                    f"An error occurred:\n{error_msg}\n\n"
                    "Please try a different video or check your connection."
                )

        finally:
            # Always release the video capture
            if vid_cap is not None:
                vid_cap.release()


def play_rtsp_stream(conf, model):
    """
    Plays an rtsp stream. Detects Objects in real-time using the YOLOv8 object detection model.

    Parameters:
        conf: Confidence of YOLOv8 model.
        model: An instance of the `YOLOv8` class containing the YOLOv8 model.

    Returns:
        None

    Raises:
        None
    """
    source_rtsp = st.sidebar.text_input("rtsp stream url:")
    st.sidebar.caption(
        'Example URL: rtsp://admin:12345@192.168.1.210:554/Streaming/Channels/101')
    is_display_tracker, tracker = display_tracker_options()
    if st.sidebar.button('Detect Objects'):
        try:
            vid_cap = cv2.VideoCapture(source_rtsp)
            st_frame = st.empty()
            while (vid_cap.isOpened()):
                success, image = vid_cap.read()
                if success:
                    _display_detected_frames(conf,
                                             model,
                                             st_frame,
                                             image,
                                             is_display_tracker,
                                             tracker
                                             )
                else:
                    vid_cap.release()
                    break
        except Exception as e:
            vid_cap.release()
            st.sidebar.error("Error loading RTSP stream: " + str(e))


def play_webcam(conf, model):
    """
    Plays a webcam stream. Detects Objects in real-time using the YOLOv8 object detection model.

    Parameters:
        conf: Confidence of YOLOv8 model.
        model: An instance of the `YOLOv8` class containing the YOLOv8 model.

    Returns:
        None

    Raises:
        None
    """
    source_webcam = settings.WEBCAM_PATH
    is_display_tracker, tracker = display_tracker_options()
    if st.sidebar.button('Detect Objects'):
        try:
            vid_cap = cv2.VideoCapture(source_webcam)
            st_frame = st.empty()
            while (vid_cap.isOpened()):
                success, image = vid_cap.read()
                if success:
                    _display_detected_frames(conf,
                                             model,
                                             st_frame,
                                             image,
                                             is_display_tracker,
                                             tracker,
                                             )
                else:
                    vid_cap.release()
                    break
        except Exception as e:
            st.sidebar.error("Error loading video: " + str(e))


def play_stored_video(conf, model):
    """
    Plays a stored video file. Tracks and detects objects in real-time using the YOLOv8 object detection model.

    Parameters:
        conf: Confidence of YOLOv8 model.
        model: An instance of the `YOLOv8` class containing the YOLOv8 model.

    Returns:
        None

    Raises:
        None
    """
    source_vid = st.sidebar.selectbox(
        "Choose a video...", settings.VIDEOS_DICT.keys())

    is_display_tracker, tracker = display_tracker_options()

    with open(settings.VIDEOS_DICT.get(source_vid), 'rb') as video_file:
        video_bytes = video_file.read()
    if video_bytes:
        st.video(video_bytes)

    if st.sidebar.button('Detect Video Objects'):
        try:
            vid_cap = cv2.VideoCapture(
                str(settings.VIDEOS_DICT.get(source_vid)))
            st_frame = st.empty()
            while (vid_cap.isOpened()):
                success, image = vid_cap.read()
                if success:
                    _display_detected_frames(conf,
                                             model,
                                             st_frame,
                                             image,
                                             is_display_tracker,
                                             tracker
                                             )
                else:
                    vid_cap.release()
                    break
        except Exception as e:
            st.sidebar.error("Error loading video: " + str(e))
