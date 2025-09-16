from port.extraction_helpers import epoch_to_date, extract_single_file_from_zip
import pandas as pd

# Patterns to find the relevant files for this behavior
patterns = ["stories"]

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Wie oft haben Sie Stories veröffentlicht und haben Sie Standortinformationen hinzugefügt? [pro Tag]",
}

def extract_stories_created(zip_file_path):
    """Extract stories created data from ZIP file -> count per day + info about location"""

    # Extract data from ZIP file
    stories_created_json = extract_single_file_from_zip(zip_file_path, patterns[0])

    if stories_created_json is None:
        return None

    results = []

    for story in stories_created_json.get("ig_stories", []):
        date = epoch_to_date(story.get("creation_timestamp", ""))
        has_latitude_data = any(
            "latitude" in exif_data
            for exif_data in story.get("media_metadata", {})
            .get("photo_metadata", {})
            .get("exif_data", [])
        )

        # Handle dummy value conversion
        if has_latitude_data in [True, "True"]:
            dummy_value = "Ja"
        elif has_latitude_data in [False, "False"]:
            dummy_value = "Nein"
        else:
            dummy_value = str(has_latitude_data)

        results.append(
            {
                "Datum": date,
                "Standortinformationen geteilt": dummy_value,
            }
        )

    stories_df = pd.DataFrame(results)

    return stories_df
