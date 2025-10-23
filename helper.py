from ultralytics import YOLO
import streamlit as st
import cv2
import yt_dlp
import torch
import settings


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


def get_youtube_stream_url(youtube_url):
    """
    Extract direct video stream URL from YouTube using yt-dlp.

    Uses multiple format fallbacks to ensure compatibility:
    1. Best MP4 video (≤720p) + M4A audio (optimal for OpenCV)
    2. Best MP4 format (≤720p)
    3. Any format (≤720p)
    4. Best available format

    Args:
        youtube_url (str): YouTube video URL

    Returns:
        str: Direct video stream URL

    Raises:
        Exception: If extraction fails or URL is invalid
    """
    ydl_opts = {
        # Format selection optimized for OpenCV compatibility
        # Prefer formats with video+audio merged (no separate streams)
        # 720p limit for better performance (detection doesn't need 4K)
        'format': (
            # First try: merged formats with reasonable resolution
            'best[height<=720][ext=mp4]/'
            'best[height<=720]/'
            # Fallback: try to merge video+audio
            'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]+bestaudio/'
            # Last resort: best available
            'best'
        ),
        'no_warnings': False,  # Show warnings for debugging
        'quiet': False,  # Show output for debugging
        'no_color': True,  # Disable color codes for Streamlit
        'socket_timeout': 30,  # Add timeout to prevent hanging
        'prefer_insecure': False,  # Prefer HTTPS
        'nocheckcertificate': False,  # Check SSL certificates
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)

            if not info:
                raise Exception("Failed to extract video information")

            # Get the direct stream URL
            # Try 'url' first, then fallback to 'manifest_url' or 'webpage_url'
            stream_url = info.get('url') or info.get('manifest_url')

            if not stream_url:
                # Some formats might have URL in 'formats' list
                formats = info.get('formats', [])
                if formats:
                    # Get the last format (usually the selected one)
                    stream_url = formats[-1].get('url')

            if not stream_url:
                raise Exception(
                    "No stream URL found in video info. "
                    "The video might be private, age-restricted, or unavailable."
                )

            # Log format info for debugging
            format_info = info.get('format', 'unknown')
            resolution = f"{info.get('width', '?')}x{info.get('height', '?')}"

            return stream_url

    except Exception as e:
        # Re-raise with more context
        raise Exception(f"YouTube extraction failed: {str(e)}")


def play_youtube_video(conf, model):
    """
    Plays a YouTube video stream with object detection and optional tracking.

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
            # Step 1: Extract video stream URL
            st.sidebar.info("Extracting video stream URL...")
            stream_url = get_youtube_stream_url(source_youtube)

            if not stream_url:
                st.sidebar.error("Failed to extract video URL. Please try again.")
                return

            # Step 2: Open video stream with OpenCV
            st.sidebar.info("Opening video stream...")
            vid_cap = cv2.VideoCapture(stream_url)

            # Step 3: Verify stream opened successfully
            if not vid_cap.isOpened():
                st.sidebar.error(
                    "Failed to open video stream. Possible causes:\n"
                    "- Video may be private or restricted\n"
                    "- Stream URL may have expired\n"
                    "- Network connectivity issues\n\n"
                    "Please try a different video or check your connection."
                )
                return

            # Get video properties for info
            fps = vid_cap.get(cv2.CAP_PROP_FPS)
            width = int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            st.sidebar.success(f"Video stream opened successfully!")
            st.sidebar.info(f"Resolution: {width}x{height} | FPS: {fps:.1f}")

            # Step 4: Process video frames with detection/tracking
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

            if "YouTube extraction failed" in error_msg:
                st.sidebar.error(
                    f"YouTube Extraction Error:\n{error_msg}\n\n"
                    "Possible solutions:\n"
                    "- Update yt-dlp: pip install --upgrade yt-dlp\n"
                    "- Check if the video is available in your region\n"
                    "- Try a different video"
                )
            elif "Broken pipe" in error_msg or "Errno 32" in error_msg:
                st.sidebar.error(
                    f"Stream Connection Error:\n{error_msg}\n\n"
                    "The video stream was interrupted. This can happen if:\n"
                    "- The stream URL expired (try again)\n"
                    "- Network connection is unstable\n"
                    "- Video format is not compatible"
                )
            else:
                st.sidebar.error(f"An error occurred:\n{error_msg}")

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
