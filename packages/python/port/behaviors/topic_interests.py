from port.extraction_helpers import extract_single_file_from_zip
import pandas as pd

# Patterns to find the relevant files for this behavior
patterns = ["recommended_topics"]

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Welche Interessen hat Instagram über Sie abgeleitet?",
}


def extract_topic_interests(zip_file_path):
    """Extract topic interests data from ZIP file -> list of topics"""

    # Extract data from ZIP file
    topic_interests_json = extract_single_file_from_zip(zip_file_path, patterns[0])

    if topic_interests_json is None:
        return None

    topics_list = [
        t["string_map_data"]["Name"]["value"]
        for t in topic_interests_json["topics_your_topics"]
    ]
    topics_df = pd.DataFrame(topics_list, columns=["Themen"])

    return topics_df
