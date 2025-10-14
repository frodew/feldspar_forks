from port.extraction_helpers import epoch_to_date
import pandas as pd
import zipfile
import json

# Patterns to find the relevant files for this behavior
patterns = ["message_1.json"]

# Title used in prompt_consent() to describe this behavior
title = {
    "de": "Wie oft haben Sie Nachrichten auf Instagram geschrieben? [pro Tag]",
}


def extract_from_zip(zip_file_path):
    """
    Extract message data from Instagram ZIP file with special handling.
    Combines messages from all conversations (inbox and message_requests).
    Returns combined messages data structure or None if not found.
    """
    try:
        with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
            file_names = zip_ref.namelist()

            # This is for messages - we need to find all message files
            all_messages_data = {"combined_messages": []}

            # Find all message files in the ZIP (look in both inbox and message_requests folders)
            message_files = []
            for name in file_names:
                if (
                    name.endswith("message_1.json")
                    and ("/inbox/" in name or "/message_requests/" in name)
                    and not name.startswith("__MACOSX/")
                    and "/._" not in name
                ):
                    message_files.append(name)

            if not message_files:
                print("No message files found")
                return None

            for message_file in message_files:
                try:
                    with zip_ref.open(message_file) as json_file:
                        json_content = json_file.read()
                        conversation_data = json.loads(json_content)

                        # Only process valid message files with participants
                        if (
                            "participants" in conversation_data
                            and len(conversation_data["participants"]) > 1
                            and "messages" in conversation_data
                        ):
                            # User is typically the second participant
                            user_name = conversation_data["participants"][1]["name"]

                            # Extract outgoing messages
                            for message in conversation_data["messages"]:
                                if (
                                    message.get("sender_name") == user_name
                                    and "timestamp_ms" in message
                                ):
                                    # Add to combined messages
                                    all_messages_data["combined_messages"].append(
                                        {
                                            "timestamp_ms": message["timestamp_ms"],
                                            "sender_name": "user1",  # Anonymize
                                            "conversation": message_file.split("/")[
                                                -2
                                            ],  # Get conversation ID
                                        }
                                    )
                except Exception as e:
                    print(f"Error reading message file {message_file}: {e}")
                    continue

            return all_messages_data

    except Exception as e:
        print(f"Error extracting messages from ZIP: {e}")
        return None


def extract_messages(zip_file_path):
    """
    Extract message counts per day from all Instagram conversations.

    This function processes the combined messages data structure that contains
    messages from all conversations in the Instagram data export.
    """

    # Extract data from ZIP file
    combined_messages_data = extract_from_zip(zip_file_path)

    if combined_messages_data is None:
        return None

    # Process all messages
    message_counts = {}

    # Check if we have the combined messages data structure
    if combined_messages_data and "combined_messages" in combined_messages_data:
        for message in combined_messages_data["combined_messages"]:
            # Convert timestamp (milliseconds) to date
            date = epoch_to_date(
                message["timestamp_ms"] // 1000
            )  # Divide by 1000 to convert ms to seconds

            # Increment count for this date
            if date in message_counts:
                message_counts[date] += 1
            else:
                message_counts[date] = 1

    # Convert to DataFrame
    if message_counts:
        dates = list(message_counts.keys())
        counts = list(message_counts.values())
        result_df = pd.DataFrame({"Datum": dates, "Anzahl": counts})
        result_df = result_df.sort_values(by="Datum").reset_index(drop=True)
        return result_df

    # Return empty DataFrame if no messages found
    return pd.DataFrame(columns=["Datum", "Anzahl"])
