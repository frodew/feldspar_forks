import json
import zipfile


def extract_single_file_from_zip(zip_file_path, pattern):
    """
    Extract a single JSON file from ZIP file based on pattern.
    Returns the JSON data or None if not found.

    Args:
        zip_file_path: Path to the ZIP file
        pattern: Pattern to match in file path (e.g., "history/watch-history")

    Returns:
        Parsed JSON data or None if file not found
    """
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
