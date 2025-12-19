import importlib
import json
import zipfile

import pandas as pd

import port.api.props as props
from port.api.assets import *
from port.api.commands import CommandSystemDonate, CommandSystemExit, CommandUIRender

############################
# MAIN FUNCTION INITIATING THE DONATION PROCESS
############################


def process(sessionId):
    key = "project_workshop_youtube"

    # STEP 1: select the file
    data = None
    while True:
        # Allow users to only upload zip-files and render file-input page
        promptFile = prompt_file("application/zip")
        fileResult = yield render_data_submission_page([promptFile])

        if fileResult.__type__ == "PayloadString":
            # Check if valid YouTube DDP
            check_ddp = check_if_valid_youtube_ddp(fileResult.value)

            if check_ddp == "valid":
                behaviors_to_extract = [
                    "watch_history",
                    "search_history",
                    "comments",
                    "subscriptions",
                ]

                extraction_result = []

                for index, behavior_name in enumerate(behaviors_to_extract, start=1):
                    percentage = (index / len(behaviors_to_extract)) * 100

                    message = f"Processing file: {behavior_name}"

                    promptMessage = prompt_extraction_message(message, percentage)
                    yield render_data_submission_page(promptMessage)

                    result = extract_behavior(behavior_name, fileResult.value)
                    extraction_result.append(result)

                if len(extraction_result) > 0:
                    data = extraction_result
                    break
                else:
                    retry_result = yield render_data_submission_page(
                        retry_confirmation()
                    )
                    if retry_result.__type__ == "PayloadTrue":
                        continue
                    else:
                        break

            elif check_ddp == "invalid_no_json":
                retry_result = yield render_data_submission_page(
                    retry_confirmation_no_json()
                )

                if retry_result.__type__ == "PayloadTrue":
                    continue

            else:  # also for invalid_no_ddp
                retry_result = yield render_data_submission_page(retry_confirmation())

                if retry_result.__type__ == "PayloadTrue":
                    continue

    # STEP 2: ask for consent
    for prompt in prompt_consent(data, behaviors_to_extract):
        result = yield prompt
        if result.__type__ == "PayloadJSON":
            data_submission_data = json.loads(result.value)
            yield donate(f"{sessionId}-{key}", json.dumps(data_submission_data))
        if result.__type__ == "PayloadFalse":
            value = json.dumps('{"status" : "data_donation declined"}')
            yield donate(f"{sessionId}-{key}", value)


############################
# HELPER FUNCTIONS IN THE DONATION PROCESS
############################


def check_if_valid_youtube_ddp(filename):
    """Check if the uploaded file is a valid YouTube data download package"""
    # Check for either English or German folder structure
    folder_name_check_ddp_en = "YouTube and YouTube Music"
    folder_name_check_ddp_de = "YouTube und YouTube Music"

    try:
        with zipfile.ZipFile(filename, "r") as zip_ref:
            found_folder_name_check_ddp = False
            found_html_file = False

            for file_info in zip_ref.infolist():
                if (
                    folder_name_check_ddp_en in file_info.filename
                    or folder_name_check_ddp_de in file_info.filename
                ):
                    found_folder_name_check_ddp = True

                # Check if any .html file exists (watch-history.html, search-history.html, etc.)
                if file_info.filename.endswith(".html"):
                    found_html_file = True

            if found_folder_name_check_ddp:
                if found_html_file:
                    print(
                        f"YouTube folder found and HTML file(s) found in the ZIP file. Seems like a YouTube HTML DDP."
                    )
                    return "invalid_no_json"

                else:
                    print(
                        f"YouTube folder found and no HTML files found in the ZIP file. Seems like a real YouTube JSON DDP."
                    )
                    return "valid"

            else:
                print(f"YouTube folder not found. Does not seem like a YouTube DDP.")
                return "invalid_no_ddp"

    except zipfile.BadZipFile:
        print("Invalid ZIP file.")
        return "invalid_file_zip"

    except Exception as e:
        print(f"An error occurred: {e}")
        return "invalid_file_error"


def extract_behavior(behavior_name, zip_file_path):
    """
    Extract data for a specific behavior using the new per-file system.

    Parameters:
    - behavior_name: Name of the behavior (e.g., 'watch_history', 'search_history')
    - zip_file_path: Path to the ZIP file

    Returns:
    - DataFrame with extracted data or error DataFrame
    """
    try:
        # Dynamically import the behavior module
        behavior_module = importlib.import_module(f"port.behaviors.{behavior_name}")

        # Get extraction function from the module
        extraction_function = getattr(behavior_module, f"extract_{behavior_name}")

        # Call the behavior's extraction function directly with ZIP file path
        try:
            result = extraction_function(zip_file_path)

            # Handle None return (missing files)
            if result is None:
                return pd.DataFrame(
                    [f'(File "{behavior_name}" missing)'],
                    columns=["No Information"],
                )

            return result
        except Exception as e:
            error_df = pd.DataFrame(
                [f"Extraction failed - {behavior_name}, {type(e).__name__}: {str(e)}"],
                columns=[str(behavior_name)],
            )
            return error_df

    except ImportError as e:
        error_df = pd.DataFrame(
            [f"Behavior '{behavior_name}' not found: {str(e)}"],
            columns=["Error"],
        )
        return error_df
    except Exception as e:
        error_df = pd.DataFrame(
            [f"Unexpected error for '{behavior_name}': {str(e)}"],
            columns=["Error"],
        )
        return error_df


def get_behavior_info(behavior_name):
    """
    Get metadata (title, patterns, etc.) for a specific behavior.

    Parameters:
    - behavior_name: Name of the behavior (e.g., 'watch_history', 'search_history')

    Returns:
    - Dictionary with behavior metadata or None if behavior not found
    """
    try:
        # Dynamically import the behavior module
        behavior_module = importlib.import_module(f"port.behaviors.{behavior_name}")

        return {
            "title": behavior_module.title,
            "patterns": behavior_module.patterns,
        }
    except ImportError:
        return None
    except Exception:
        return None


def prompt_consent(data, behaviors_list):
    """
    Consent prompting function that works with the new behavior system.
    This is a generator function that properly yields like the original prompt_consent.
    """
    description = props.PropsUIPromptText(
        text=props.Translatable(
            {
                "en": "Here you can find all the data you can donate to us. If you do not want to donate certain data, you can delete or modify it."
            }
        )
    )

    # Initialize lists to store data
    table_data_list = []

    if data is not None:
        for i, behavior_name in enumerate(behaviors_list):
            df = data[i]

            # Get behavior info from the behavior file
            behavior_info = get_behavior_info(behavior_name)
            if behavior_info is None:
                # Fallback if behavior info cannot be retrieved
                behavior_title = {"en": f"Unknown Behavior: {behavior_name}"}
            else:
                behavior_title = {"en": behavior_info["title"]["en"]}

            # Clean DataFrame for JSON serialization
            df_cleaned = df.copy()

            # Convert all columns to string to avoid serialization issues
            for col in df_cleaned.columns:
                df_cleaned[col] = df_cleaned[col].fillna("").astype(str)

            df = df_cleaned

            # Store table data for later creation with correct numbering
            table_data_list.append(
                {"behavior_name": behavior_name, "title": behavior_title, "df": df}
            )
    # Create all tables with correct sequential numbering
    table_list = []
    for i, table_data in enumerate(table_data_list, start=1):
        table = props.PropsUIPromptConsentFormTable(
            table_data["behavior_name"],
            i,
            props.Translatable(table_data["title"]),
            props.Translatable(
                table_data["title"]
            ),  # Using title as description for now
            table_data["df"],
        )
        table_list.append(table)

    # Construct and render the final consent page
    consent_items = []
    consent_items.append(description)
    consent_items.extend(table_list)

    donation_buttons = props.PropsUIDataSubmissionButtons(
        donate_question=props.Translatable(
            {"en": "Would you like to donate the above data?"}
        ),
        donate_button=props.Translatable({"en": "Yes, donate"}),
    )
    consent_items.append(donation_buttons)

    result = yield render_data_submission_page(
        [item for item in consent_items if item is not None]
    )

    return result


############################
# RENDER PAGES AND PROMPT MESSAGES
############################


def render_data_submission_page(body):
    header = props.PropsUIHeader(props.Translatable({"en": "YouTube Data Donation"}))

    # Convert single body item to array if needed
    body_items = [body] if not isinstance(body, list) else body
    page = props.PropsUIPageDataSubmission("Zip", header, body_items)
    return CommandUIRender(page)


def retry_confirmation():
    text = props.Translatable(
        {
            "en": "Unfortunately we cannot process your file. Are you sure you selected your downloaded YouTube data?"
        }
    )
    ok = props.Translatable({"en": "Try again"})

    return props.PropsUIPromptConfirm(text, ok)


def retry_confirmation_no_json():
    text = props.Translatable(
        {
            "en": 'Unfortunately we cannot process your file. It seems you accidentally requested the HTML version of your YouTube data.\nPlease request your data again from YouTube and select "JSON" as the file format (as described in the instructions).'
        }
    )

    ok = props.Translatable({"en": "Try again with correct data"})

    return props.PropsUIPromptConfirm(text, ok)


def prompt_file(extensions):
    description = props.Translatable(
        {"en": "Please select your downloaded YouTube ZIP file."}
    )

    return props.PropsUIPromptFileInput(description, extensions)


def prompt_extraction_message(message, percentage):
    description = props.Translatable(
        {
            "en": "One moment please. Information is now being extracted from the selected file."
        }
    )

    return props.PropsUIPromptProgress(description, message, percentage)


def donate(key, json_string):
    return CommandSystemDonate(key, json_string)


def exit(code, info):
    return CommandSystemExit(code, info)
