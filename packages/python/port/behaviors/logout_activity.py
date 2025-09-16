from port.extraction_helpers import extract_single_file_from_zip
import pandas as pd
from datetime import datetime

# Patterns to find the relevant files for this behavior
patterns = ["logout_activity"]

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Wann und mit welchem Gerät/Browser haben Sie sich bei Instagram abgemeldet?",
}

def extract_logout_activity(zip_file_path):
    """Extract logout activity data from ZIP file -> time and user agent"""

    # Extract data from ZIP file
    logout_activity_json = extract_single_file_from_zip(zip_file_path, patterns[0])

    if logout_activity_json is None:
        return None

    logouts = logout_activity_json["account_history_logout_history"]

    timestamps = [t["title"] for t in logouts]
    dates = [str(datetime.fromisoformat(timestamp).date()) for timestamp in timestamps]
    times = [datetime.fromisoformat(timestamp).time() for timestamp in timestamps]

    user_agents = [t["string_map_data"]["User Agent"]["value"] for t in logouts]

    logout_df = pd.DataFrame({"Datum": dates, "Uhrzeit": times, "Gerät/Browser": user_agents})

    return logout_df
