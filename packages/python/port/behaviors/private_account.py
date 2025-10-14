from port.extraction_helpers import extract_single_file_from_zip
import pandas as pd

# Patterns to find the relevant files for this behavior
patterns = ["personal_information/personal_information.json"]

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Haben Sie ein privates (nicht öffentliches) Konto auf Instagram?",
}


def extract_private_account(zip_file_path):
    """Extract private account data from ZIP file -> dummies whether user has private account"""

    # Extract data from ZIP file
    personal_information_json = extract_single_file_from_zip(zip_file_path, patterns[0])

    if personal_information_json is None:
        return None

    # check if information present
    private_account = None

    for k in ["Private Account", "Privates Konto"]:  # keys are language specific
        if k in personal_information_json["profile_user"][0]["string_map_data"]:
            private_account = personal_information_json["profile_user"][0][
                "string_map_data"
            ][k]["value"]
            break

    # Handle dummy value conversion
    if private_account in [True, "True"]:
        dummy_value = "Ja"
    elif private_account in [False, "False"]:
        dummy_value = "Nein"
    else:
        dummy_value = str(private_account)

    return pd.DataFrame([dummy_value], columns=["Privates Konto"])
