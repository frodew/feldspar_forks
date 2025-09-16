from port.extraction_helpers import extract_single_file_from_zip
import pandas as pd

# Patterns to find the relevant files for this behavior
patterns = ["personal_information/personal_information.json"]

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Haben Sie eine E-Mail-Adresse in Ihrem Profil?",
}

def extract_email_address(zip_file_path):
    """Extract email address data from ZIP file -> dummy whether user has email"""

    # Extract data from ZIP file
    personal_information_json = extract_single_file_from_zip(zip_file_path, patterns[0])

    if personal_information_json is None:
        return None

    # Check if email information is present
    email = None

    for k in ["Email", "E-Mail-Adresse"]:  # keys are language specific
        if k in personal_information_json["profile_user"][0]["string_map_data"]:
            email = (
                personal_information_json["profile_user"][0]["string_map_data"][k]["value"] != "False"
            )
            break

    # Handle dummy value conversion
    if email in [True, "True"]:
        dummy_value = "Ja"
    elif email in [False, "False"]:
        dummy_value = "Nein"
    else:
        dummy_value = str(email)

    return pd.DataFrame([dummy_value], columns=["Email"])
