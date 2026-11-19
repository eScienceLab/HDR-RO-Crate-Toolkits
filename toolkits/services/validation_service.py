import json

from toolkits.clients.validation_client import validate_rocrate_metadata


def is_rocrate_metadata_valid(crate_metadata: dict) -> bool:
    """Return True when the data is valid RO-Crate metadata.

    This function serialises the RO-Crate metadata into JSON formatted string,
    sends it to the validation client, and reads the `status` of the response,
    which the RO-Crate Validation Service sets to "valid", "invalid" or "error".

    Args:
        crate_metadata (dict): The RO-Crate metadata to validate.

    Returns:
        True if `status` is "valid", False if it is "invalid".

    Raises:
        TypeError: If `crate_metadata` is not a dictionary.
        ValueError: If `status` is missing or has any other value.
    """

    if not isinstance(crate_metadata, dict):
        raise TypeError("crate_metadata must be a dictionary")

    serialised_metadata = json.dumps(crate_metadata)
    response_json = validate_rocrate_metadata(serialised_metadata)
    status = response_json.get("status")

    if status == "valid":
        return True
    if status == "invalid":
        return False

    message = f"Unexpected validation status: {status!r}"
    if response_json.get("error"):
        message += f" ({response_json['error']})"
    raise ValueError(message)
