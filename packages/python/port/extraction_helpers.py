from port.api.assets import *
from port.api.props import Translatable
import pandas as pd
from datetime import datetime, timezone, timedelta
import zipfile
import cv2
import numpy as np
import time


def epoch_to_date(epoch_timestamp: str | int) -> str:
    """
    Convert epoch timestamp to an ISO 8601 string. Assumes UTC +1

    If timestamp cannot be converted raise CannotConvertEpochTimestamp
    """

    try:
        epoch_timestamp = int(epoch_timestamp)
        out = datetime.fromtimestamp(
            epoch_timestamp, tz=timezone(timedelta(hours=1))
        ).isoformat()  # timezone = utc + 1

    except:
        # fake date if unable to convert
        out = "01-01-1999"

    out = pd.to_datetime(out)
    return out.date().strftime(
        "%d-%m-%Y"
    )  # convertion to string for display in browser


def extract_single_file_from_zip(zip_file_path, pattern):
    """
    Extract a single JSON file from Instagram ZIP file based on pattern.
    Returns the JSON data or None if not found.
    """
    import zipfile
    import json

    try:
        with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
            file_names = zip_ref.namelist()

            # Find and load file matching pattern
            for file_name in file_names:
                if file_name.endswith(".json") and pattern in file_name:
                    try:
                        with zip_ref.open(file_name) as json_file:
                            json_content = json_file.read()
                            return json.loads(json_content)
                    except Exception as e:
                        print(f"Error reading {pattern} file {file_name}: {e}")

            return None

    except Exception as e:
        print(f"Error extracting {pattern} from ZIP: {e}")
        return None


def extract_multiple_files_from_zip(zip_file_path, patterns, key_mapping=None):
    """
    Extract multiple JSON files from Instagram ZIP file based on patterns.
    Returns a dictionary mapping pattern names (or mapped keys) to their JSON data.

    Args:
        zip_file_path: Path to the ZIP file
        patterns: List of file patterns to search for
        key_mapping: Optional dict mapping patterns to result keys
    """
    import zipfile
    import json

    try:
        with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
            file_names = zip_ref.namelist()
            result = {}

            # Find and load files for each pattern
            for pattern in patterns:
                pattern_data = None
                for file_name in file_names:
                    if file_name.endswith(".json") and pattern in file_name:
                        try:
                            with zip_ref.open(file_name) as json_file:
                                json_content = json_file.read()
                                pattern_data = json.loads(json_content)
                                break
                        except Exception as e:
                            print(f"Error reading {pattern} file {file_name}: {e}")

                # Use key mapping if provided, otherwise use pattern as key
                result_key = (
                    key_mapping.get(pattern, pattern) if key_mapping else pattern
                )
                result[result_key] = pattern_data or {}

            # Return combined data structure if any files found
            if any(data for data in result.values() if data):
                return result
            else:
                return None

    except Exception as e:
        print(f"Error extracting multiple files from ZIP: {e}")
        return None


def detect_faces_in_images(zip_file_path, image_uris):
    """
    Detect faces in images from a ZIP file with improved accuracy.

    Uses OpenCV-only implementation with optimized single-pass detection for improved accuracy.

    Dependency reduction: Removed PIL dependency, now uses only OpenCV for image processing.

    Args:
        zip_file_path: Path to the ZIP file
        image_uris: List of image URIs to analyze

    Returns:
        Dictionary mapping URIs to True/False based on face detection
    """
    face_dict = {}

    # Load face cascade classifier
    try:
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
    except Exception as e:
        print(f"Error loading face cascade classifier: {e}")
        # Return False for all images if classifier can't be loaded
        return {uri: False for uri in image_uris}

    # Set the desired size for the images
    target_width, target_height = 300, 300

    try:
        with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
            for uri in image_uris:
                try:
                    # Check if the file exists in the zip and is a jpg image
                    if uri.lower().endswith(".jpg") and uri in zip_ref.namelist():
                        # Open the image file within the zip file
                        with zip_ref.open(uri) as img_file:
                            start_time = time.time()  # Record start time

                            # Load the image from bytes using OpenCV
                            img_data = img_file.read()
                            img_array = np.frombuffer(img_data, np.uint8)
                            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

                            if img is None:
                                face_dict[uri] = False
                                continue

                            # Convert to grayscale using OpenCV
                            img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

                            # Resize the image using OpenCV
                            img_down_np = cv2.resize(
                                img_gray,
                                (target_width, target_height),
                                interpolation=cv2.INTER_LANCZOS4,
                            )

                            # Single optimized detection pass
                            faces = face_cascade.detectMultiScale(
                                img_down_np,
                                scaleFactor=1.08,
                                minNeighbors=3,
                                minSize=(18, 18),
                            )

                            end_time = time.time()  # Record end time
                            processing_time = (
                                end_time - start_time
                            )  # Calculate processing time
                            print(
                                "Processing time for {}: {:.2f} seconds".format(
                                    uri, processing_time
                                )
                            )

                            # Set result based on face detection
                            face_dict[uri] = len(faces) > 0

                    else:
                        # Image not found or not a jpg file
                        face_dict[uri] = False

                except Exception as e:
                    print(f"Error processing image {uri}: {e}")
                    face_dict[uri] = False

    except Exception as e:
        print(f"Error opening ZIP file for face detection: {e}")
        # Return False for all images if ZIP can't be opened
        return {uri: False for uri in image_uris}

    return face_dict
