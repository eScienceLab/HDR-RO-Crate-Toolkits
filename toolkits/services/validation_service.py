import json

from toolkits.clients.validation_client import validate_rocrate_metadata


def is_rocrate_metadata_valid(data):
    result = validate_rocrate_metadata(data).get("result", "{}")
    try:
        result_json = json.loads(result)
    except (TypeError, ValueError):
        return False
    return result_json.get("passed", False)
