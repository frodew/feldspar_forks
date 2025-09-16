from port.api.assets import *
from port.api.props import Translatable
import pandas as pd
from datetime import datetime, timezone, timedelta


def epoch_to_date(epoch_timestamp: str | int) -> str:
    """
    Convert epoch timestamp to an ISO 8601 string. Assumes UTC +1

    If timestamp cannot be converted raise CannotConvertEpochTimestamp
    """

    try:
        epoch_timestamp = int(epoch_timestamp)
        out = datetime.fromtimestamp(
            epoch_timestamp, tz=timezone(timedelta(hours=1))
        ).isoformat()  # timezone = utc + 1

    except:
        # fake date if unable to convert
        out = "01-01-1999"

    out = pd.to_datetime(out)
    return out.date().strftime(
        "%d-%m-%Y"
    )  # convertion to string for display in browser




def extract_single_file_from_zip(zip_file_path, pattern):
    """
    Extract a single JSON file from Instagram ZIP file based on pattern.
    Returns the JSON data or None if not found.
    """
    import zipfile
    import json

    try:
        with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
            file_names = zip_ref.namelist()

            # Find and load file matching pattern
            for file_name in file_names:
                if file_name.endswith(".json") and pattern in file_name:
                    try:
                        with zip_ref.open(file_name) as json_file:
                            json_content = json_file.read()
                            return json.loads(json_content)
                    except Exception as e:
                        print(f"Error reading {pattern} file {file_name}: {e}")

            return None

    except Exception as e:
        print(f"Error extracting {pattern} from ZIP: {e}")
        return None


def extract_multiple_files_from_zip(zip_file_path, patterns, key_mapping=None):
    """
    Extract multiple JSON files from Instagram ZIP file based on patterns.
    Returns a dictionary mapping pattern names (or mapped keys) to their JSON data.

    Args:
        zip_file_path: Path to the ZIP file
        patterns: List of file patterns to search for
        key_mapping: Optional dict mapping patterns to result keys
    """
    import zipfile
    import json

    try:
        with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
            file_names = zip_ref.namelist()
            result = {}

            # Find and load files for each pattern
            for pattern in patterns:
                pattern_data = None
                for file_name in file_names:
                    if file_name.endswith(".json") and pattern in file_name:
                        try:
                            with zip_ref.open(file_name) as json_file:
                                json_content = json_file.read()
                                pattern_data = json.loads(json_content)
                                break
                        except Exception as e:
                            print(f"Error reading {pattern} file {file_name}: {e}")

                # Use key mapping if provided, otherwise use pattern as key
                result_key = key_mapping.get(pattern, pattern) if key_mapping else pattern
                result[result_key] = pattern_data or {}

            # Return combined data structure if any files found
            if any(data for data in result.values() if data):
                return result
            else:
                return None

    except Exception as e:
        print(f"Error extracting multiple files from ZIP: {e}")
        return None
