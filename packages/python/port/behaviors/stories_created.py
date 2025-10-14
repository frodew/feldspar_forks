from port.extraction_helpers import (
    epoch_to_date,
    extract_single_file_from_zip,
    detect_faces_in_images,
)
import pandas as pd

# Patterns to find the relevant files for this behavior
patterns = ["stories"]

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Wie oft haben Sie Stories veröffentlicht, haben Sie Standortinformationen hinzugefügt und ist ein Gesicht sichtbar?",
}


def extract_stories_created(zip_file_path):
    """Extract stories created data from ZIP file -> count per day + info about location"""

    # Extract data from ZIP file
    stories_created_json = extract_single_file_from_zip(zip_file_path, patterns[0])

    if stories_created_json is None:
        return None

    results = []
    image_uris = []

    # First pass: collect all image URIs and basic data
    for story in stories_created_json.get("ig_stories", []):
        uri = story.get("uri", "")
        if uri and uri.lower().endswith(".jpg"):
            image_uris.append(uri)

        date = epoch_to_date(story.get("creation_timestamp", ""))
        has_latitude_data = any(
            "latitude" in exif_data
            for exif_data in story.get("media_metadata", {})
            .get("photo_metadata", {})
            .get("exif_data", [])
        )

        # Handle dummy value conversion for location
        if has_latitude_data in [True, "True"]:
            location_value = "Ja"
        elif has_latitude_data in [False, "False"]:
            location_value = "Nein"
        else:
            location_value = str(has_latitude_data)

        results.append(
            {
                "Datum": date,
                "Standortinformationen geteilt": location_value,
                "uri": uri,
            }
        )

    # Detect faces in all images
    face_detection_results = detect_faces_in_images(zip_file_path, image_uris)

    # Add face detection results to each row
    for result in results:
        uri = result.get("uri", "")

        # Check if there's an image file at all
        if not uri or not uri.lower().endswith(".jpg"):
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

    stories_df = pd.DataFrame(results)

    return stories_df
