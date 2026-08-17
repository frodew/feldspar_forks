import importlib
import json
import logging
import zipfile

import pandas as pd

import port.api.props as props
from port.api.assets import *
from port.api.commands import CommandSystemDonate, CommandSystemExit, CommandUIRender, FlushLogs

logger = logging.getLogger(__name__)

############################
# MAIN FUNCTION INITIATING THE DONATION PROCESS
############################

# Row cap applied to each behavior's table when it's shown in the consent form and donated (via PropsUIPromptConsentFormTable.data_frame_max_size).
BEHAVIOR_ROW_CAPS = {
    "watch_history": 50000,
    "search_history": 20000,
    "comments": 10000,
    "subscriptions": 10000,
}


def process(data):
    # `data` is a context dict routed from the JS framework: {"sessionId": "...", "locale": "..."}
    sessionId = data.get("sessionId")
    locale = data.get("locale", "de")
    key = "radical_dd"

    logger.info(f"user entered script (locale={locale})")

    # STEP 1: select the file
    data_result = None
    while True:
        # Allow users to only upload zip-files and render file-input page
        promptFile = prompt_file("application/zip")
        fileResult = yield render_data_submission_page([promptFile])

        if fileResult.__type__ == "PayloadFile":
            # Check if valid YouTube DDP
            check_ddp = check_if_valid_youtube_ddp(fileResult.value)
            yield FlushLogs

            if check_ddp in ("valid", "valid_my_activity"):
                behaviors_to_extract = [
                    "watch_history",
                    "search_history",
                    "subscriptions",
                ]
                if check_ddp == "valid":
                    # Comments aren't present in "My Activity" exports, so
                    # there's nothing to extract - skip it rather than show
                    # participants a table that's always empty.
                    behaviors_to_extract.insert(2, "comments")

                extraction_result = []

                for index, behavior_name in enumerate(behaviors_to_extract, start=1):
                    percentage = (index / len(behaviors_to_extract)) * 100

                    message = f"Processing file: {behavior_name}"

                    promptMessage = prompt_extraction_message(message, percentage)
                    yield render_data_submission_page(promptMessage)

                    result = extract_behavior(behavior_name, fileResult.value)
                    extraction_result.append(result)
                    yield FlushLogs

                if len(extraction_result) > 0:
                    data_result = extraction_result
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
    for prompt in prompt_consent(data_result, behaviors_to_extract):
        result = yield prompt
        if result.__type__ == "PayloadJSON":
            data_submission_data = json.loads(result.value)
            logger.info("participant consented, donating data")
            yield donate(f"{sessionId}-{key}", json.dumps(data_submission_data))
        if result.__type__ == "PayloadFalse":
            logger.info("participant declined data donation")
            value = json.dumps('{"status" : "data_donation declined"}')
            yield donate(f"{sessionId}-{key}", value)


############################
# HELPER FUNCTIONS IN THE DONATION PROCESS
############################


def check_if_valid_youtube_ddp(file):
    """Check if the uploaded file is a valid YouTube data download package"""
    try:
        with zipfile.ZipFile(file, "r") as zip_ref:
            found_folder_name_check_ddp = False
            found_html_file = False

            for file_info in zip_ref.infolist():
                if (
                    "YouTube" in file_info.filename
                    and "YouTube Music" in file_info.filename
                ):
                    found_folder_name_check_ddp = True

                # Check if any .html file exists (watch-history.html, search-history.html, etc.)
                if file_info.filename.endswith(".html"):
                    found_html_file = True

            if found_folder_name_check_ddp:
                if found_html_file:
                    logger.info(
                        "YouTube folder found and HTML file(s) found in the ZIP file. Seems like a YouTube HTML DDP."
                    )
                    return "invalid_no_json"

                else:
                    logger.info(
                        "YouTube folder found and no HTML files found in the ZIP file. Seems like a real YouTube JSON DDP."
                    )
                    return "valid"

            # Not a YouTube-product DDP by folder name. It might instead be a Google "My Activity" export - its top-level folder name is localized ("Meine Aktivitäten", "My Activity", ...), so the brand-name check above doesn't apply. Detect it by content instead: a JSON file shaped like a My Activity export (a list of entries carrying English, non-localized keys).
            if check_if_my_activity_export(zip_ref):
                logger.info(
                    'YouTube folder not found, but a "My Activity"-shaped JSON file was. Seems like a YouTube My Activity DDP.'
                )
                return "valid_my_activity"

            logger.info("YouTube folder not found. Does not seem like a YouTube DDP.")
            return "invalid_no_ddp"

    except zipfile.BadZipFile:
        logger.warning("Invalid ZIP file.")
        return "invalid_file_zip"

    except Exception as e:
        logger.exception(f"An error occurred while validating the zip file: {e}")
        return "invalid_file_error"


def check_if_my_activity_export(zip_ref):
    """
    Check whether the ZIP contains a JSON file shaped like a Google "My
    Activity" export: a list of entries where most carry the "time" and
    "products" keys. Those keys are always in English regardless of the
    export's locale, unlike file/folder names, so this works without
    knowing the participant's language.
    """
    for file_info in zip_ref.infolist():
        if not file_info.filename.endswith(".json"):
            continue
        try:
            with zip_ref.open(file_info.filename) as json_file:
                data = json.loads(json_file.read().decode("utf-8"))
        except Exception:
            continue

        if not isinstance(data, list) or not data:
            continue

        sample = data[:20]
        matches = sum(
            1
            for entry in sample
            if isinstance(entry, dict) and "time" in entry and "products" in entry
        )
        if matches >= max(1, len(sample) // 2):
            return True

    return False


def extract_behavior(behavior_name, file):
    """
    Extract data for a specific behavior using the new per-file system.

    Parameters:
    - behavior_name: Name of the behavior (e.g., 'watch_history', 'search_history')
    - file: File-like object for the uploaded ZIP

    Returns:
    - DataFrame with extracted data or error DataFrame
    """
    try:
        # Dynamically import the behavior module
        behavior_module = importlib.import_module(f"port.behaviors.{behavior_name}")

        # Get extraction function from the module
        extraction_function = getattr(behavior_module, f"extract_{behavior_name}")

        # Call the behavior's extraction function directly with the file
        try:
            result = extraction_function(file)

            # Handle None return (missing files)
            if result is None:
                logger.info(f"{behavior_name}: file missing in DDP")
                return pd.DataFrame(
                    [f'(File "{behavior_name}" missing)'],
                    columns=["No Information"],
                )

            logger.info(f"{behavior_name}: extracted {len(result)} rows")
            return result
        except Exception as e:
            logger.exception(f"Extraction failed for behavior '{behavior_name}'")
            error_df = pd.DataFrame(
                [f"Extraction failed - {behavior_name}, {type(e).__name__}: {str(e)}"],
                columns=[str(behavior_name)],
            )
            return error_df

    except ImportError as e:
        logger.exception(f"Behavior '{behavior_name}' not found")
        error_df = pd.DataFrame(
            [f"Behavior '{behavior_name}' not found: {str(e)}"],
            columns=["Error"],
        )
        return error_df
    except Exception as e:
        logger.exception(f"Unexpected error for behavior '{behavior_name}'")
        error_df = pd.DataFrame(
            [f"Unexpected error for '{behavior_name}': {str(e)}"],
            columns=["Error"],
        )
        return error_df


def get_behavior_info(behavior_name):
    """
    Get metadata (title) for a specific behavior.

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
                "de": "Hier finden Sie nun alle Daten, die Sie an uns spenden können. Wenn Sie bestimmte Daten nicht spenden wollen, können Sie diese löschen oder anpassen."
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
                behavior_title = {"de": f"Unbekanntes Verhalten: {behavior_name}"}
            else:
                behavior_title = {"de": behavior_info["title"]["de"]}

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
            data_frame_max_size=BEHAVIOR_ROW_CAPS.get(
                table_data["behavior_name"], 10000
            ),
        )
        table_list.append(table)

    # Construct and render the final consent page
    consent_items = []
    consent_items.append(description)
    consent_items.extend(table_list)

    donation_buttons = props.PropsUIDataSubmissionButtons(
        donate_question=props.Translatable(
            {"de": "Möchten Sie die obenstehenden Daten spenden?"}
        ),
        donate_button=props.Translatable({"de": "Ja, spenden"}),
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
    header = props.PropsUIHeader(props.Translatable({"de": "YouTube Datenspende"}))

    # Convert single body item to array if needed
    body_items = [body] if not isinstance(body, list) else body
    page = props.PropsUIPageDataSubmission("Zip", header, body_items)
    return CommandUIRender(page)


def retry_confirmation():
    text = props.Translatable(
        {
            "de": "Leider können wir Ihre Datei nicht bearbeiten. Sind Sie sicher, dass Sie Ihre heruntergeladenen YouTube-Daten ausgewählt haben?"
        }
    )
    ok = props.Translatable({"de": "Erneut versuchen"})

    return props.PropsUIPromptConfirm(text, ok)


def retry_confirmation_no_json():
    text = props.Translatable(
        {
            "de": 'Leider können wir Ihre Datei nicht verarbeiten. Es scheint so, dass Sie aus Versehen die HTML-Version Ihrer YouTube-Daten beantragt haben.\nBitte beantragen Sie erneut eine Datenspende bei YouTube und wählen Sie dabei "JSON" als Dateiformat aus (wie in der Anleitung beschrieben).'
        }
    )

    ok = props.Translatable({"de": "Erneut versuchen mit richtigen Daten"})

    return props.PropsUIPromptConfirm(text, ok)


def prompt_file(extensions):
    description = props.Translatable(
        {"de": "Bitte wählen Sie Ihre heruntergeladene YouTube ZIP-Datei aus."}
    )

    return props.PropsUIPromptFileInput(description, extensions)


def prompt_extraction_message(message, percentage):
    description = props.Translatable(
        {
            "de": "Einen Moment bitte. Es werden nun Informationen aus der ausgewählten Datei extrahiert."
        }
    )

    return props.PropsUIPromptProgress(description, message, percentage)


def donate(key, json_string):
    return CommandSystemDonate(key, json_string)


def exit(code, info):
    return CommandSystemExit(code, info)
