import requests

from urllib.parse import urljoin
from toolkits.config.settings import CRATEY_VALIDATOR_API_URL

def validate_rocrate_metadata(serialised_metadata: str) -> dict:
    """Validate a RO-Crate metadata by sending it to validation API.
    
    This function wraps a serialised RO-Crate metadata into request payload of 
    the form {"crate_json": <metadata_json>} and sends it to the validation API
    endpoint via HTTP POST request. Successful responses are expected to contain
    a JSON body, which is returned as a dictionary.

    Args:
        serialised_metadata (str): A JSON object serialised as a string.

    Returns:
        The parsed JSON response from the API.

    Raises:
        TypeError: If `serialised_metadata` is not a string.
        requests.exceptions.RequestException: If the request failed.
        ValueError: If the response body cannot be decoded as JSON.
    """

    if not isinstance(serialised_metadata, str):
        raise TypeError("serialised_metadata must be a string")

    url = urljoin(CRATEY_VALIDATOR_API_URL, "v1/ro_crates/validate_metadata")
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {"crate_json": serialised_metadata}
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()
