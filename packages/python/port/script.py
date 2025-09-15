import port.api.props as props
from port.api.assets import *
from port.api.commands import CommandSystemDonate, CommandSystemExit, CommandUIRender

import pandas as pd
import zipfile
import json
import time

# import extraction functions and dictionaries for all platforms
from port.instagram_extraction_functions import *
from port.instagram_extraction_functions_dict import (
    extraction_dict
)

def process(sessionId):
    locale = "de"
    key = "instagram-data-donation-main-study"

    # STEP 1: select the file
    data = None
    while True:
        # Allow users to only upload zip-files and render file-input page
        promptFile = prompt_file("application/zip")
        fileResult = yield render_data_submission_page([promptFile])

        if fileResult.__type__ == "PayloadString":
            # Check if valid Instagram DDP
            check_ddp = check_if_valid_instagram_ddp(fileResult.value)

            if check_ddp == "valid":
                extraction_result = []

                fileCount = len(extraction_dict)

                # Extracting the zipfile
                for index, (file, entry) in enumerate(extraction_dict.items(), start=1):
                    percentage = (index / fileCount) * 100
                    promptMessage = prompt_extraction_message(
                        f"Extracting file: {file}", percentage
                    )
                    yield render_data_submission_page(promptMessage)

                    # Get list of possible file names (sometimes language sensitive)
                    patterns = entry.get("patterns", [file])

                    file_content, matched_pattern = extract_instagram_content_from_zip_folder(fileResult.value, file, patterns)

                    if file_content is not None:
                        try:
                            # Call the extraction function with content
                            file_extraction_result = entry["extraction_function"](file_content, locale)
                        except Exception as e:
                            file_extraction_result = pd.DataFrame(
                                [f"Extrahierung fehlgeschlagen - {file}, {type(e).__name__}: {str(e)}"],
                                columns=[str(file)],
                            )
                    else:
                        file_extraction_result = pd.DataFrame(
                            [f'(Datei "{str(file)}" fehlt)'],
                            columns=["Keine Informationen"],
                        )

                    extraction_result.append(file_extraction_result)

                if len(extraction_result) > 0:
                    data = extraction_result
                    break
                else:
                    retry_result = yield render_data_submission_page(retry_confirmation())
                    if retry_result.__type__ == "PayloadTrue":
                        continue
                    else:
                        break


            elif (
                check_ddp == "invalid_no_json"
            ):
                retry_result = yield render_data_submission_page(
                    retry_confirmation_no_json()
                )

                if retry_result.__type__ == "PayloadTrue":
                    continue

            elif check_ddp == "invalid_no_ddp":
                # Use platform-specific error messages
                retry_result = yield render_data_submission_page(
                    retry_confirmation_no_ddp()
                )

                if retry_result.__type__ == "PayloadTrue":
                    continue

            else:
                retry_result = yield render_data_submission_page(
                    retry_confirmation_no_ddp()
                )

                if retry_result.__type__ == "PayloadTrue":
                    continue

    # STEP 2: ask for consent
    for prompt in prompt_consent(data):
        result = yield prompt
        if result.__type__ == "PayloadJSON":
            meta_frame = pd.DataFrame([1], columns=["type", "message"])
            data_submission_data = json.loads(result.value)
            data_submission_data["meta"] = meta_frame.to_json()
            yield donate(f"{sessionId}-{key}", json.dumps(data_submission_data))
        if result.__type__ == "PayloadFalse":
            value = json.dumps('{"status" : "data_submission declined"}')
            yield donate(f"{sessionId}-{key}", value)

def check_if_valid_instagram_ddp(filename):
    """Check if the uploaded file is a valid Instagram data download package"""
    folder_name_check_ddp = "ads_information"
    file_name_check_html = "start_here.html"

    try:
        with zipfile.ZipFile(filename, "r") as zip_ref:
            found_folder_name_check_ddp = False
            found_file_name_check_html = False

            for file_info in zip_ref.infolist():
                if folder_name_check_ddp in file_info.filename:
                    found_folder_name_check_ddp = True

                if file_name_check_html in file_info.filename:
                    found_file_name_check_html = True

            if found_folder_name_check_ddp:
                if found_file_name_check_html:
                    print(
                        f"Folder '{folder_name_check_ddp}' found and file '{file_name_check_html}' found in the ZIP file. Seems like a Instagram HTML DDP."
                    )
                    return "invalid_no_json"

                else:
                    print(
                        f"Folder '{folder_name_check_ddp}' found and file '{file_name_check_html}' not found in the ZIP file. Seems like a real Instagram JSON DDP."
                    )
                    return "valid"

            else:
                print(
                    f"Folder '{folder_name_check_ddp}' not found. Does not seem like an Instagram DDP."
                )
                return "invalid_no_ddp"

    except zipfile.BadZipFile:
        print("Invalid ZIP file.")
        return "invalid_file_zip"

    except Exception as e:
        print(f"An error occurred: {e}")
        return "invalid_file_error"

def extract_instagram_content_from_zip_folder(zip_file_path, file_key, patterns):
    """
    Extract JSON content from Instagram data export zip file based on the file key.

    Parameters:
    - zip_file_path: Path to the zip file
    - file_key: The key from extraction_dict (e.g., 'messages', 'time_spent')
    - patterns: File patterns to look for (used as fallback)

    Special handling for:
    1. Message files - combines all conversations
    2. Time spent/sessions - loads posts_viewed and/or videos_watched
    """
    try:
        with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
            # Get the list of file names in the zip file
            file_names = zip_ref.namelist()

            # Special handling for messages
            if file_key == "messages":
                # This is for messages - we need to find all message files
                all_messages_data = {"combined_messages": []}

                # Find all message files in the ZIP (look in both inbox and message_requests folders)
                message_files = []
                for name in file_names:
                    if name.endswith("message_1.json") and (
                        "/inbox/" in name or "/message_requests/" in name
                    ):
                        message_files.append(name)

                if not message_files:
                    print("No message files found")
                    return None, "message_1.json"

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

                return all_messages_data, "message_1.json"

            # Special handling for time_spent and session_frequency which need posts_viewed and/or videos_watched
            if file_key == "time_spent" or file_key == "session_frequency":
                # We need to load either or both files
                posts_viewed_data = None
                videos_watched_data = None

                # Find and load posts_viewed.json
                for file_name in file_names:
                    if file_name.endswith(".json") and "posts_viewed" in file_name:
                        try:
                            with zip_ref.open(file_name) as json_file:
                                json_content = json_file.read()
                                posts_viewed_data = json.loads(json_content)
                                break
                        except Exception as e:
                            print(f"Error reading posts_viewed file {file_name}: {e}")

                # Find and load videos_watched.json
                for file_name in file_names:
                    if file_name.endswith(".json") and "videos_watched" in file_name:
                        try:
                            with zip_ref.open(file_name) as json_file:
                                json_content = json_file.read()
                                videos_watched_data = json.loads(json_content)
                                break
                        except Exception as e:
                            print(f"Error reading videos_watched file {file_name}: {e}")

                # Combine the data for the extraction function - work with either or both files
                if posts_viewed_data or videos_watched_data:
                    combined_data = {
                        "posts_viewed": posts_viewed_data or {},
                        "videos_watched": videos_watched_data or {},
                    }
                    return combined_data, "combined_viewing_data"
                else:
                    print("Could not find posts_viewed or videos_watched files")
                    return None, "combined_viewing_data"

            # Special handling for combined_views (posts + videos)
            if file_key == "combined_views":
                posts_viewed_data = None
                videos_watched_data = None

                # Find and load posts_viewed.json
                for file_name in file_names:
                    if file_name.endswith(".json") and "posts_viewed" in file_name:
                        try:
                            with zip_ref.open(file_name) as json_file:
                                json_content = json_file.read()
                                posts_viewed_data = json.loads(json_content)
                                break
                        except Exception as e:
                            print(f"Error reading posts_viewed file {file_name}: {e}")

                # Find and load videos_watched.json
                for file_name in file_names:
                    if file_name.endswith(".json") and "videos_watched" in file_name:
                        try:
                            with zip_ref.open(file_name) as json_file:
                                json_content = json_file.read()
                                videos_watched_data = json.loads(json_content)
                                break
                        except Exception as e:
                            print(f"Error reading videos_watched file {file_name}: {e}")

                # Combine the data
                if posts_viewed_data or videos_watched_data:
                    combined_data = {
                        "posts_viewed": posts_viewed_data or {},
                        "videos_watched": videos_watched_data or {},
                    }
                    return combined_data, "combined_views"
                else:
                    print("Could not find posts_viewed or videos_watched files")
                    return None, "combined_views"

            # Special handling for combined_blocks (blocked + restricted profiles)
            if file_key == "combined_blocks":
                blocked_data = None
                restricted_data = None

                # Find and load blocked_profiles.json
                for file_name in file_names:
                    if file_name.endswith(".json") and "blocked_profiles" in file_name:
                        try:
                            with zip_ref.open(file_name) as json_file:
                                json_content = json_file.read()
                                blocked_data = json.loads(json_content)
                                break
                        except Exception as e:
                            print(f"Error reading blocked_profiles file {file_name}: {e}")

                # Find and load restricted_profiles.json
                for file_name in file_names:
                    if file_name.endswith(".json") and "restricted_profiles" in file_name:
                        try:
                            with zip_ref.open(file_name) as json_file:
                                json_content = json_file.read()
                                restricted_data = json.loads(json_content)
                                break
                        except Exception as e:
                            print(f"Error reading restricted_profiles file {file_name}: {e}")

                # Combine the data
                if blocked_data or restricted_data:
                    combined_data = {
                        "blocked_profiles": blocked_data or {},
                        "restricted_profiles": restricted_data or {},
                    }
                    return combined_data, "combined_blocks"
                else:
                    print("Could not find blocked_profiles or restricted_profiles files")
                    return None, "combined_blocks"

            # Special handling for combined_comments (post + reel comments)
            if file_key == "combined_comments":
                post_comments_data = None
                reel_comments_data = None

                # Find and load post_comments.json
                for file_name in file_names:
                    if file_name.endswith(".json") and "post_comments_1" in file_name:
                        try:
                            with zip_ref.open(file_name) as json_file:
                                json_content = json_file.read()
                                post_comments_data = json.loads(json_content)
                                break
                        except Exception as e:
                            print(f"Error reading post_comments file {file_name}: {e}")

                # Find and load reels_comments.json
                for file_name in file_names:
                    if file_name.endswith(".json") and "reels_comments" in file_name:
                        try:
                            with zip_ref.open(file_name) as json_file:
                                json_content = json_file.read()
                                reel_comments_data = json.loads(json_content)
                                break
                        except Exception as e:
                            print(f"Error reading reels_comments file {file_name}: {e}")

                # Combine the data
                if post_comments_data or reel_comments_data:
                    combined_data = {
                        "post_comments": post_comments_data or {},
                        "reel_comments": reel_comments_data or {},
                    }
                    return combined_data, "combined_comments"
                else:
                    print("Could not find post_comments or reels_comments files")
                    return None, "combined_comments"

            # Special handling for combined_likes (posts + stories + comments)
            if file_key == "combined_likes":
                posts_liked_data = None
                stories_liked_data = None
                comments_liked_data = None

                # Find and load liked_posts.json
                for file_name in file_names:
                    if file_name.endswith(".json") and "liked_posts" in file_name:
                        try:
                            with zip_ref.open(file_name) as json_file:
                                json_content = json_file.read()
                                posts_liked_data = json.loads(json_content)
                                break
                        except Exception as e:
                            print(f"Error reading liked_posts file {file_name}: {e}")

                # Find and load story_likes.json
                for file_name in file_names:
                    if file_name.endswith(".json") and "story_likes" in file_name:
                        try:
                            with zip_ref.open(file_name) as json_file:
                                json_content = json_file.read()
                                stories_liked_data = json.loads(json_content)
                                break
                        except Exception as e:
                            print(f"Error reading story_likes file {file_name}: {e}")

                # Find and load liked_comments.json
                for file_name in file_names:
                    if file_name.endswith(".json") and "liked_comments" in file_name:
                        try:
                            with zip_ref.open(file_name) as json_file:
                                json_content = json_file.read()
                                comments_liked_data = json.loads(json_content)
                                break
                        except Exception as e:
                            print(f"Error reading liked_comments file {file_name}: {e}")

                # Combine the data
                if posts_liked_data or stories_liked_data or comments_liked_data:
                    combined_data = {
                        "posts_liked": posts_liked_data or {},
                        "stories_liked": stories_liked_data or {},
                        "comments_liked": comments_liked_data or {},
                    }
                    return combined_data, "combined_likes"
                else:
                    print("Could not find liked_posts, story_likes, or liked_comments files")
                    return None, "combined_likes"

            # Special handling for combined_story_interactions (all story interactions)
            if file_key == "combined_story_interactions":
                countdowns_data = None
                emoji_sliders_data = None
                polls_data = None
                questions_data = None
                quizzes_data = None

                # Find and load all story interaction files
                interaction_types = ["countdowns", "emoji_sliders", "polls", "questions", "quizzes"]
                for interaction_type in interaction_types:
                    for file_name in file_names:
                        if file_name.endswith(".json") and interaction_type in file_name:
                            try:
                                with zip_ref.open(file_name) as json_file:
                                    json_content = json_file.read()
                                    data = json.loads(json_content)
                                    if interaction_type == "countdowns":
                                        countdowns_data = data
                                    elif interaction_type == "emoji_sliders":
                                        emoji_sliders_data = data
                                    elif interaction_type == "polls":
                                        polls_data = data
                                    elif interaction_type == "questions":
                                        questions_data = data
                                    elif interaction_type == "quizzes":
                                        quizzes_data = data
                                    break
                            except Exception as e:
                                print(f"Error reading {interaction_type} file {file_name}: {e}")

                # Combine the data
                if any([countdowns_data, emoji_sliders_data, polls_data, questions_data, quizzes_data]):
                    combined_data = {
                        "countdowns": countdowns_data or {},
                        "emoji_sliders": emoji_sliders_data or {},
                        "polls": polls_data or {},
                        "questions": questions_data or {},
                        "quizzes": quizzes_data or {},
                    }
                    return combined_data, "combined_story_interactions"
                else:
                    print("Could not find any story interaction files")
                    return None, "combined_story_interactions"

             # Regular handling for search history
            if file_key == "search_history":
                for file_name in file_names:
                    if (
                        file_name.endswith(".json")
                        and "word_or_phrase_searches" in file_name
                    ):
                        try:
                            with zip_ref.open(file_name) as json_file:
                                json_content = json_file.read()
                                data = json.loads(json_content)
                                return data, "word_or_phrase_searches"
                        except Exception as e:
                            print(f"Error reading search file {file_name}: {e}")

            # Regular handling for other files
            for pattern in patterns:
                for file_name in file_names:
                    if file_name.endswith(".json") and pattern in file_name:
                        try:
                            # Read the JSON file
                            with zip_ref.open(file_name) as json_file:
                                json_content = json_file.read()
                                data = json.loads(json_content)
                                return data, pattern
                        except Exception as e:
                            print(f"Error reading file {file_name}: {e}")
                            continue  # Try the next matching file if there's an error

            # If we've checked all files and found no match
            print(f"No file matching pattern '{patterns}' found for key '{file_key}'")
            return None, None

    except Exception as e:
        print(f"Error extracting Instagram content: {e}")
        return None, None


def render_data_submission_page(body):
    header = props.PropsUIHeader(
        props.Translatable(
            {
                "de": "Instagram Datenspende",
            }
        )
    )

    # Convert single body item to array if needed
    body_items = [body] if not isinstance(body, list) else body
    page = props.PropsUIPageDataSubmission("Zip", header, body_items)
    return CommandUIRender(page)


def retry_confirmation():
    text = props.Translatable(
        {
            "de": "Leider können wir Ihre Datei nicht bearbeiten. Fahren Sie fort, wenn Sie sicher sind, dass Sie die richtige Datei ausgewählt haben. Versuchen Sie, eine andere Datei auszuwählen.",
        }
    )
    ok = props.Translatable(
        {
            "de": "Erneut versuchen",
        }
    )
    cancel = props.Translatable(
        {"de": "Weiter"}
    )
    return props.PropsUIPromptConfirm(text, ok, cancel)

def retry_confirmation_no_json():
    text = props.Translatable(
        {
            "de": 'Leider können wir Ihre Datei nicht verarbeiten. Es scheint so, dass Sie aus Versehen die HTML-Version Ihrer Instagram-Daten beantragt haben.\nBitte beantragen Sie erneut eine Datenspende bei Instagram und wählen Sie dabei "JSON" als Dateivormat aus (wie in der Anleitung beschrieben).'
        }
    )

    ok = props.Translatable(
        {
            "de": "Erneut versuchen mit richtigen Daten"
        }
    )

    cancel = props.Translatable(
        {"de": "Weiter"}
    )

    return props.PropsUIPromptConfirm(text, ok, cancel)


def retry_confirmation_no_ddp():
    text = props.Translatable(
        {
            "de": f"Leider können wir Ihre Datei nicht verarbeiten. Haben Sie wirklich Ihre Instagram-Daten ausgewählt?"
        }
    )

    ok = props.Translatable(
        {"de": "Erneut versuchen"}
    )

    cancel = props.Translatable(
        {"de": "Weiter"}
    )

    return props.PropsUIPromptConfirm(text, ok, cancel)




def prompt_file(extensions):
    description = props.Translatable(
        {
            "de": "Bitte wählen Sie eine ZIP-Datei auf Ihrem Gerät aus.",
        }
    )



    return props.PropsUIPromptFileInput(description, extensions)


def prompt_extraction_message(message, percentage):
    description = props.Translatable(
        {
            "de": "Einen Moment bitte. Es werden nun Informationen aus der ausgewählten Datei extrahiert.",
        }
    )

    return props.PropsUIPromptProgress(description, message, percentage)


def prompt_consent(data):
    description = props.PropsUIPromptText(
        text=props.Translatable(
            {
                "de": "Bitte überprüfen Sie Ihre Daten unten. Verwenden Sie die Suchfelder, um bestimmte Informationen zu finden. Sie können alle Daten entfernen, die Sie nicht teilen möchten. Vielen Dank für Ihre Unterstützung dieses Forschungsprojekts!",
            }
        )
    )

    # Initialize lists to store data
    binary_data = []
    table_list = []

    if data is not None:  # can happen if user submits wrong file and still continues
        for i, (file, entry_description) in enumerate(extraction_dict.items()):
            df = data[i]

            # Clean DataFrame for JSON serialization
            df_cleaned = df.copy()

            # Convert all columns to string to avoid serialization issues
            for col in df_cleaned.columns:
                # Convert NaN to empty string, other values to string
                df_cleaned[col] = df_cleaned[col].fillna('').astype(str)

            df = df_cleaned

            # Check if the dataframe has only one row
            if len(df) == 1:
                # Extract the title from the translation
                translated_title = entry_description["title"]["de"]
                # Combine values from all columns into a single string
                combined_value = " | ".join(
                    [f"{col}: {df.iloc[0][col]}" for col in df.columns]
                )
                binary_data.append([translated_title, combined_value])
            else:
                # Directly add multi-row dataframes to the table list
                table = props.PropsUIPromptConsentFormTable(
                    file,
                    i,
                    props.Translatable(entry_description["title"]),
                    props.Translatable(entry_description.get("description", entry_description["title"])),
                    df,
                )
                table_list.append(table)

        # Create a dataframe for binary data if there are any single-row entries
        if binary_data:
            binary_df = pd.DataFrame(binary_data, columns=["Kategorie", "Daten"])
            table = props.PropsUIPromptConsentFormTable(
                "binary_results",
                99,
                props.Translatable(
                    {
                        "de": "Einzelne Informationen",
                    }
                ),
                props.Translatable(
                    {
                        "de": "Übersicht, wo wenig oder keine Instagram-Informationen vorliegen",
                    }
                ),
                binary_df,
            )
            table_list.append(table)

    # Construct and render the final consent page
    consent_items = []

    consent_items.append(description)
    consent_items.extend(table_list)

    donation_buttons = props.PropsUIDataSubmissionButtons(
        donate_question=props.Translatable(
            {
                "de": "Möchten Sie die obenstehenden Daten spenden?",
            }
        ),
        donate_button=props.Translatable(
            {
                "de": "Ja, spenden",
            }
        ),
    )
    consent_items.append(donation_buttons)

    result = yield render_data_submission_page(
        [item for item in consent_items if item is not None]
    )

    return result


def donate(key, json_string):
    return CommandSystemDonate(key, json_string)


def exit(code, info):
    return CommandSystemExit(code, info)
