import importlib
import json
import logging

import pandas as pd

import port.api.props as props
from port.api.assets import *
from port.api.commands import CommandSystemDonate, CommandSystemExit, CommandUIRender, FlushLogs
from port.ddp import YoutubeDdp

logger = logging.getLogger(__name__)

############################
# MAIN FUNCTION INITIATING THE DONATION PROCESS
############################


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
            # Parsing a large HTML export takes seconds; keep the page informed.
            yield render_data_submission_page(
                prompt_extraction_message("Reading file", 0)
            )

            ddp = YoutubeDdp(fileResult.value)
            logger.info(
                f"DDP verdict={ddp.verdict}, {len(ddp.entries)} YouTube activity "
                f"entries from [{ddp.sources}], "
                f"subscriptions csv={ddp.subscriptions_csv_source or 'none'}, "
                f"comments csv={ddp.comments_csv_source or 'none'}"
            )
            yield FlushLogs

            if ddp.verdict == "valid":
                behaviors_to_extract = ["watch_history", "search_history"]
                if ddp.comments_csv is not None:
                    # Only a YouTube-DDP has comments; skip the empty table.
                    behaviors_to_extract.append("comments")
                behaviors_to_extract.append("subscriptions")

                extraction_result = []
                sources = {}

                for index, behavior_name in enumerate(behaviors_to_extract, start=1):
                    percentage = (index / len(behaviors_to_extract)) * 100

                    message = f"Processing file: {behavior_name}"

                    promptMessage = prompt_extraction_message(message, percentage)
                    yield render_data_submission_page(promptMessage)

                    result = extract_behavior(behavior_name, ddp)
                    extraction_result.append(result)
                    sources[behavior_name] = result.attrs.get("source", "")
                    yield FlushLogs

                data_result = extraction_result
                break

            else:  # invalid_no_ddp, invalid_file_zip, invalid_file_error
                retry_result = yield render_data_submission_page(retry_confirmation())

                if retry_result.__type__ == "PayloadTrue":
                    continue

    # STEP 2: ask for consent
    for prompt in prompt_consent(data_result, behaviors_to_extract):
        result = yield prompt
        if result.__type__ == "PayloadJSON":
            data_submission_data = json.loads(result.value)
            add_source_metadata(data_submission_data, sources)
            logger.info("participant consented, donating data")
            yield donate(f"{sessionId}-{key}", json.dumps(data_submission_data))
        if result.__type__ == "PayloadFalse":
            logger.info("participant declined data donation")
            value = json.dumps('{"status" : "data_donation declined"}')
            yield donate(f"{sessionId}-{key}", value)


############################
# HELPER FUNCTIONS IN THE DONATION PROCESS
############################


def add_source_metadata(data_submission_data, sources):
    """Record for each donated table which ZIP member it came from.

    This is what tells the two DDP types apart once the ZIP is gone: a
    YouTube-DDP's subscriptions come from a CSV with no subscribe events, a
    MyActivity-DDP's from the activity file.
    """
    for table_id, source in sources.items():
        table = data_submission_data.get(table_id)
        if isinstance(table, dict):
            table.setdefault("metadata", {})["source"] = source


def extract_behavior(behavior_name, source):
    """
    Extract data for a specific behavior.

    Parameters:
    - behavior_name: Name of the behavior (e.g., 'watch_history', 'search_history')
    - source: a YoutubeDdp, or the uploaded ZIP to build one from

    Returns:
    - DataFrame with extracted data or error DataFrame
    """
    try:
        # Dynamically import the behavior module
        behavior_module = importlib.import_module(f"port.behaviors.{behavior_name}")

        # Get extraction function from the module
        extraction_function = getattr(behavior_module, f"extract_{behavior_name}")

        try:
            result = extraction_function(source)

            # Handle None return (nothing of this behavior in the DDP)
            if result is None:
                logger.info(f"{behavior_name}: no rows in DDP")
                return pd.DataFrame(
                    [f'(File "{behavior_name}" missing)'],
                    columns=["No Information"],
                )

            logger.info(
                f"{behavior_name}: extracted {len(result)} rows "
                f"from {result.attrs.get('source', '')}"
            )
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
            # No cap: show and donate every row.
            data_frame_max_size=None,
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
