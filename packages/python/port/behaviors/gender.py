from port.extraction_helpers import extract_single_file_from_zip
import pandas as pd

# Patterns to find the relevant files for this behavior
patterns = ["personal_information/personal_information.json"]

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Haben Sie Ihr Geschlecht in Ihrem Profil angegeben?",
}

def extract_gender(zip_file_path):
    """Extract gender data from ZIP file -> dummy whether user has specified gender"""

    # Extract data from ZIP file
    personal_information_json = extract_single_file_from_zip(zip_file_path, patterns[0])

    if personal_information_json is None:
        return None

    # Check if gender information is present and specified
    gender_specified = False

    for k in ["Gender", "Geschlecht"]:  # keys are language specific
        if k in personal_information_json["profile_user"][0]["string_map_data"]:
            gender_value = personal_information_json["profile_user"][0]["string_map_data"][k]["value"]
            # Check if gender is specified and not "unspecified"
            if gender_value and gender_value.lower() != "unspecified":
                gender_specified = True
            break

    # Handle dummy value conversion
    if gender_specified:
        dummy_value = "Ja"
    else:
        dummy_value = "Nein"

    return pd.DataFrame([dummy_value], columns=["Geschlecht"])
