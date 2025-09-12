import port.api.props as props
from port.api.assets import *
from port.api.commands import CommandSystemDonate, CommandSystemExit, CommandUIRender

import pandas as pd
import zipfile
import json
import time


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
                # Extracting the zipfile
                extraction_result = []
                zipfile_ref = get_zipfile(fileResult.value)
                print(zipfile_ref, fileResult.value)
                files = get_files(zipfile_ref)
                fileCount = len(files)
                for index, filename in enumerate(files):
                    percentage = ((index + 1) / fileCount) * 100
                    promptMessage = prompt_extraction_message(
                        f"Extracting file: {filename}", percentage
                    )
                    yield render_data_submission_page(promptMessage)
                    file_extraction_result = extract_file(zipfile_ref, filename)
                    extraction_result.append(file_extraction_result)

                if len(extraction_result) >= 0:
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
                print(check_ddp)
                
                retry_result = yield render_data_submission_page(
                    retry_confirmation_no_json()
                )

                if retry_result.__type__ == "PayloadTrue":
                    continue

            elif check_ddp == "invalid_no_ddp":
                print(check_ddp)
                
                # Use platform-specific error messages
                retry_result = yield render_data_submission_page(
                    retry_confirmation_no_ddp()
                )

                if retry_result.__type__ == "PayloadTrue":
                    continue

            else:
                
                print(check_ddp)
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


def get_zipfile(filename):
    try:
        return zipfile.ZipFile(filename)
    except zipfile.error:
        return "invalid"


def get_files(zipfile_ref):
    try:
        return zipfile_ref.namelist()
    except zipfile.error:
        return []


def extract_file(zipfile_ref, filename):
    try:
        # make it slow for demo reasons only
        time.sleep(0.01)
        info = zipfile_ref.getinfo(filename)
        return (filename, info.compress_size, info.file_size)
    except zipfile.error:
        return "invalid"


def prompt_consent(data):
    description = props.PropsUIPromptText(
        text=props.Translatable(
            {
                "de": "Bitte überprüfen Sie Ihre Daten unten. Verwenden Sie die Suchfelder, um bestimmte Informationen zu finden. Sie können alle Daten entfernen, die Sie nicht teilen möchten. Vielen Dank für Ihre Unterstützung dieses Forschungsprojekts!",
            }
        )
    )
    
    table_title = props.Translatable(
        {
            "de": "Inhalt der ZIP-Datei",
        }
    )

    # Show data table if extracted data is available
    data_table = None
    if data is not None:
        data_frame = pd.DataFrame(data, columns=["filename", "compressed_size", "size"])
        data_table = props.PropsUIPromptConsentFormTable(
            "zip_content",
            1,
            table_title,
            props.Translatable(
                {
                    "de": "Die Tabelle unten zeigt den Inhalt der ZIP-Datei, die Sie gewählt haben.",
                }
            ),
            data_frame,
            headers={
                "filename": props.Translatable(
                    {
                        "de": "Dateiname",
                    }
                ),
                "compressed_size": props.Translatable(
                    {
                        "de": "Komprimierte Größe",
                    }
                ),
                "size": props.Translatable(
                    {
                        "de": "Dekomprimierte Größe",
                    }
                ),
            },
        )

    # A generic, illustrative second table for layout demonstration purposes
    metadata_table = props.PropsUIPromptConsentFormTable(
        "example_metadata",
        2,
        props.Translatable(
            {
                "de": "Beispieltabelle für Metadaten",
            }
        ),
        props.Translatable(
            {
                "de": "Diese Beispieltabelle zeigt, dass mehrere Tabellen angezeigt werden können. Ihr Inhalt ist statisch und steht in keinem Zusammenhang mit Ihrer hochgeladenen Datei.",
  
            }
        ),
        pd.DataFrame(
            [
                ["participant-001", "Device A", "2025-06-01"],
                ["participant-002", "Device B", "2025-06-02"],
                ["participant-003", "Device C", "2025-06-03"],
            ],
            columns=["Participant ID", "Device", "Date"],
        ),
        headers={
                "Participant ID": props.Translatable(
                    {
                        "de": "Teilnehmer-ID",
                    }
                ),
                "Device": props.Translatable(
                    {
                        "de": "Gerät",
                    }
                ),
                "Date": props.Translatable(
                    {
                        "de": "Datum",
                    }
                ),
            },
        )
    
    # Construct and render the final consent page
    result = yield render_data_submission_page(
        [
            item
            for item in [
                description,
                data_table,
                metadata_table,
                props.PropsUIDataSubmissionButtons(
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
                ),
            ]
            if item is not None
        ]
    )
    return result


def donate(key, json_string):
    return CommandSystemDonate(key, json_string)


def exit(code, info):
    return CommandSystemExit(code, info)
