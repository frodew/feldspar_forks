from port.extraction_helpers import extract_single_file_from_zip, detect_faces_in_images
import pandas as pd

# Patterns to find the relevant files for this behavior
patterns = ["profile_photos"]

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Ist auf Ihrem Profilfoto ein Gesicht sichtbar?",
}

def extract_profile_picture(zip_file_path):
    """Extract profile picture data from ZIP file and detect faces"""

    # Extract data from ZIP file
    profile_photos_json = extract_single_file_from_zip(zip_file_path, patterns[0])

    if profile_photos_json is None:
        return None

    results = []
    image_uris = []

    # Extract profile photo URIs
    for photo in profile_photos_json.get("ig_profile_picture", []):
        uri = photo.get("uri", "")
        if uri and uri.lower().endswith((".jpg", ".jpeg", ".png")):
            image_uris.append(uri)

        results.append(
            {
                "uri": uri,
            }
        )

    # If no profile photos found at all, create a single empty entry
    if not results:
        results.append({"uri": ""})

    # Detect faces in all profile images
    face_detection_results = detect_faces_in_images(zip_file_path, image_uris)

    # Add face detection results to each row
    for result in results:
        uri = result.get("uri", "")

        # Check if there's an image file at all
        if not uri or not uri.lower().endswith((".jpg", ".jpeg", ".png")):
            face_value = "Kein Bild"
        else:
            has_face = face_detection_results.get(uri, False)
            # Handle dummy value conversion for face detection
            if has_face:
                face_value = "Ja"
            else:
                face_value = "Nein"

        result["Gesicht erkannt"] = face_value
        # Remove URI as it's not needed in final output
        del result["uri"]

    profile_df = pd.DataFrame(results)

    return profile_df
