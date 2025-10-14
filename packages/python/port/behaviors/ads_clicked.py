from port.extraction_helpers import epoch_to_date, extract_multiple_files_from_zip
import pandas as pd

# Patterns to find the relevant files for this behavior
patterns = ["ads_clicked", "link_history/link_history.json"]

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Wie oft haben Sie Werbung angeklickt? [pro Tag]",
}


def extract_ads_clicked_data(ads_clicked_json):
    """Extract ads clicked data from ads_clicked JSON"""

    if (
        not ads_clicked_json
        or "impressions_history_ads_clicked" not in ads_clicked_json
    ):
        return pd.DataFrame(columns=["Datum", "Angeklickte Werbung"])

    try:
        timestamps = [
            t["string_list_data"][0]["timestamp"]
            for t in ads_clicked_json["impressions_history_ads_clicked"]
        ]  # get list with timestamps in epoch format
        dates = [epoch_to_date(t) for t in timestamps]  # convert epochs to dates
        products = [
            i["title"] for i in ads_clicked_json["impressions_history_ads_clicked"]
        ]

        ads_clicked_df = pd.DataFrame({"Datum": dates, "Angeklickte Werbung": products})
        return ads_clicked_df
    except Exception as e:
        print(f"Error extracting ads_clicked data: {e}")
        return pd.DataFrame(columns=["Datum", "Angeklickte Werbung"])


def extract_link_history_data(link_history_json):
    """Extract link history data from link_history JSON"""

    if not link_history_json or not isinstance(link_history_json, list):
        return pd.DataFrame(columns=["Datum", "Angeklickte Werbung"])

    try:
        dates = []
        titles = []

        for entry in link_history_json:
            if (
                not isinstance(entry, dict)
                or "timestamp" not in entry
                or "label_values" not in entry
            ):
                continue

            # Extract timestamp and convert to date
            timestamp = entry["timestamp"]
            date = epoch_to_date(timestamp)

            # Extract title from the second item in label_values
            label_values = entry["label_values"]
            if isinstance(label_values, list) and len(label_values) >= 2:
                # Check if the website URL (first item) contains accountscenter.instagram.com
                url_entry = label_values[0]
                if (
                    isinstance(url_entry, dict)
                    and url_entry.get("label") == "Website link you visited"
                ):
                    url_value = url_entry.get("value", "")
                    if "accountscenter.instagram.com" in url_value:
                        continue  # Skip this entry

                title_entry = label_values[1]
                if (
                    isinstance(title_entry, dict)
                    and title_entry.get("label") == "Title of website page you visited"
                ):
                    title_value = title_entry.get("value", "")
                    if title_value:  # Only add non-empty titles
                        dates.append(date)
                        titles.append(title_value)

        link_history_df = pd.DataFrame({"Datum": dates, "Angeklickte Werbung": titles})
        return link_history_df
    except Exception as e:
        print(f"Error extracting link_history data: {e}")
        return pd.DataFrame(columns=["Datum", "Angeklickte Werbung"])


def extract_ads_clicked(zip_file_path):
    """Extract ads clicked and link history data from ZIP file -> list of product names per day"""

    # Extract data from ZIP file
    combined_data = extract_multiple_files_from_zip(zip_file_path, patterns)

    if combined_data is None:
        return None

    # Initialize an empty DataFrame to store the combined results
    combined_df = pd.DataFrame(columns=["Datum", "Angeklickte Werbung"])

    # Extract ads clicked data if available
    ads_clicked_data = combined_data.get(patterns[0], {})
    if ads_clicked_data:
        ads_clicked_df = extract_ads_clicked_data(ads_clicked_data)
        if not ads_clicked_df.empty:
            combined_df = pd.concat([combined_df, ads_clicked_df], ignore_index=True)

    # Extract link history data if available
    link_history_data = combined_data.get(patterns[1], [])
    if link_history_data:
        link_history_df = extract_link_history_data(link_history_data)
        if not link_history_df.empty:
            combined_df = pd.concat([combined_df, link_history_df], ignore_index=True)

    if combined_df.empty:
        return None

    # Group by date and aggregate the clicked items into lists
    aggregated_df = (
        combined_df.groupby("Datum")["Angeklickte Werbung"].agg(list).reset_index()
    )

    return aggregated_df
