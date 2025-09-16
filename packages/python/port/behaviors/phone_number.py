from port.extraction_helpers import extract_single_file_from_zip
import pandas as pd

# Patterns to find the relevant files for this behavior
patterns = ["personal_information/personal_information.json"]

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Haben Sie eine Telefonnummer in Ihrem Profil?",
}

def extract_phone_number(zip_file_path):
    """Extract phone number data from ZIP file -> dummy whether user has phone confirmed"""

    # Extract data from ZIP file
    personal_information_json = extract_single_file_from_zip(zip_file_path, patterns[0])

    if personal_information_json is None:
        return None

    # Check if phone information is present
    phone = None

    for k in [
        "Phone Confirmed",
        "Telefonnummer best\u00c3\u00a4tigt",
    ]:  # keys are language specific
        if k in personal_information_json["profile_user"][0]["string_map_data"]:
            phone = (
                personal_information_json["profile_user"][0]["string_map_data"][k]["value"] != "False"
            )
            break

    # Handle dummy value conversion
    if phone in [True, "True"]:
        dummy_value = "Ja"
    elif phone in [False, "False"]:
        dummy_value = "Nein"
    else:
        dummy_value = str(phone)

    return pd.DataFrame([dummy_value], columns=["Telefon"])
