import requests

from urllib.parse import urljoin
from toolkits.config.settings import CRATEY_VALIDATOR_API_URL

def validate_rocrate_metadata(data):
    """Send payload to the RO-Crate metatdata validation API and return the response."""

    url = urljoin(CRATEY_VALIDATOR_API_URL, "v1/ro_crates/validate_metadata")
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    json_data = {"crate_json": data}
    response = requests.post(url, headers=headers, json=json_data)
    return response.json()
