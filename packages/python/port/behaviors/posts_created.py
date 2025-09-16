from port.extraction_helpers import epoch_to_date, extract_single_file_from_zip
import pandas as pd

# Patterns to find the relevant files for this behavior
patterns = ["posts_1"]

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Wie oft haben Sie Posts veröffentlicht und hatten Sie Standortinformationen hinzugefügt? [pro Tag]",
}

def extract_posts_created(zip_file_path):
    """Extract posts created data from ZIP file -> count per day + info about location"""

    # Extract data from ZIP file
    posts_created_json = extract_single_file_from_zip(zip_file_path, patterns[0])

    if posts_created_json is None:
        return None

    results = []

    # file can just be dict and not list if only one post
    if isinstance(posts_created_json, dict):
        for media in posts_created_json.get("media", []):
            date = epoch_to_date(media.get("creation_timestamp", ""))
            has_latitude_data = any(
                "latitude" in exif_data
                for exif_data in media.get("media_metadata", {})
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

    else:
        for post in posts_created_json:
            for media in post.get("media", []):
                date = epoch_to_date(media.get("creation_timestamp", ""))
                has_latitude_data = any(
                    "latitude" in exif_data
                    for exif_data in media.get("media_metadata", {})
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

    posts_df = pd.DataFrame(results)

    return posts_df
