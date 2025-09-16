from port.extraction_helpers import extract_single_file_from_zip
import pandas as pd

# Patterns to find the relevant files for this behavior
patterns = ["instagram_profile_information"]

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Haben Sie die Kontaktsynchronisierung aktiviert?",
}

def extract_contact_syncing(zip_file_path):
    """Extract contact syncing data from ZIP file -> dummy whether 'contact_syncing' is enabled"""

    # Extract data from ZIP file
    contact_syncing_json = extract_single_file_from_zip(zip_file_path, patterns[0])

    if contact_syncing_json is None:
        return None

    value = None

    for k in [
        "Contact Syncing",
        "Kontaktsynchronisierung",
        "Synchronisation des contacts",
    ]:  # keys are language specific
        if k in contact_syncing_json["profile_account_insights"][0]["string_map_data"]:
            value = contact_syncing_json["profile_account_insights"][0][
                "string_map_data"
            ][k]["value"]
            break

    # Handle dummy value conversion
    if value in [True, "True"]:
        dummy_value = "Ja"
    elif value in [False, "False"]:
        dummy_value = "Nein"
    else:
        dummy_value = str(value)

    return pd.DataFrame([dummy_value], columns=["Kontaktsynchronisierung aktiviert"])
