from port.extraction_helpers import extract_single_file_from_zip
import pandas as pd
from datetime import datetime

# Patterns to find the relevant files for this behavior
patterns = ["login_activity"]

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Wann und mit welchem Gerät/Browser haben Sie sich bei Instagram angemeldet?",
}

def extract_login_activity(zip_file_path):
    """Extract login activity data from ZIP file -> time and user agent"""

    # Extract data from ZIP file
    login_activity_json = extract_single_file_from_zip(zip_file_path, patterns[0])

    if login_activity_json is None:
        return None

    logins = login_activity_json["account_history_login_history"]

    timestamps = [t["title"] for t in logins]
    dates = [str(datetime.fromisoformat(timestamp).date()) for timestamp in timestamps]
    times = [datetime.fromisoformat(timestamp).time() for timestamp in timestamps]

    user_agents = [t["string_map_data"]["User Agent"]["value"] for t in logins]

    login_df = pd.DataFrame({"Datum": dates, "Uhrzeit": times, "Gerät/Browser": user_agents})

    return login_df
