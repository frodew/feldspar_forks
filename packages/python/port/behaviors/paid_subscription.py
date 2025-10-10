from port.extraction_helpers import extract_single_file_from_zip
import pandas as pd

# Patterns to find the relevant files for this behavior
patterns = ["subscription_for_no_ads"]

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Nutzen Sie Instagrams kostenpflichtige Abo-Option, mit der Ihnen keine Werbeinhalte angezeigt werden?",
}


def extract_paid_subscription(zip_file_path):
    """Extract paid subscription data from ZIP file -> dummy whether user has subscription for no ads"""

    # Extract data from ZIP file
    subscription_json = extract_single_file_from_zip(zip_file_path, patterns[0])

    if subscription_json is None:
        return None

    value = None

    if subscription_json["label_values"][0]["value"]:
        value = str(subscription_json["label_values"][0]["value"])
    else:
        value = "Keine Information"

    return pd.DataFrame([value], columns=["Abo-Option für Werbefreiheit"])
