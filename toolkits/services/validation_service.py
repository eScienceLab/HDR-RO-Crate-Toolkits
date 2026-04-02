import json

from typing import Dict
from toolkits.clients.validation_client import validate_rocrate_metadata


def is_rocrate_metadata_valid(crate_metadata: Dict) -> bool:
    """Return True when the data is valid RO-Crate metadata.
    
    This function serialises the RO-Crate metadata into JSON formatted string,
    gets response json from validation client, and process the results to 
    to return True or False.

    Args:
        crate_metadata (Dict): The RO-Crate metadata to validate.

    Returns:
        True if `passed` key exists and is True, else False.
    
    Raises:
        TypeError: If `crate_metadata` is not a dictionary.
        ValueError: If `result` contains invalid JSON.
    """

    if not isinstance(crate_metadata, dict):
        raise TypeError("crate_metadata must be a dictionary")

    serialised_metadata = json.dumps(crate_metadata)
    response_json = validate_rocrate_metadata(serialised_metadata)
    result = response_json.get("result", "{}")

    if isinstance(result, str):
        try:
            result_json = json.loads(result)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON in 'result'")

    return result_json.get("passed", False)
