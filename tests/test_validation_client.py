import pytest
import requests

from unittest.mock import Mock, patch

from toolkits.clients.validation_client import validate_rocrate_metadata


MOCK_API_URL = "https://cratey.validator.api"
SERIALISED_METADATA = '{"@context": "https://w3id.org/ro/crate/1.2/context"}'

@patch("toolkits.clients.validation_client.requests.post")
def test_validate_rocrate_metadata(mock_post):
    mock_response = Mock()
    mock_response.json.return_value = {'result': '{\n    "passed": true,\n    "issues": []\n}'}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    with patch("toolkits.clients.validation_client.CRATEY_VALIDATOR_API_URL", MOCK_API_URL):
        response_json = validate_rocrate_metadata(SERIALISED_METADATA)

    # requests.post should be called with the following
    url = MOCK_API_URL + "/v1/ro_crates/validate_metadata"
    headers = {"accept": "application/json", "Content-Type": "application/json"}
    payload = {"crate_json": SERIALISED_METADATA}

    mock_post.assert_called_once_with(url, headers=headers, json=payload)
    assert response_json == {'result': '{\n    "passed": true,\n    "issues": []\n}'}

def test_validate_rocrate_metadata_non_string_input():
    with pytest.raises(TypeError, match="serialised_metadata must be a string"):
        validate_rocrate_metadata({"not": "string"})

@patch("toolkits.clients.validation_client.requests.post")
def test_validate_rocrate_metadata_http_error(mock_post):
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError
    mock_post.return_value = mock_response

    with pytest.raises(requests.exceptions.HTTPError):
        validate_rocrate_metadata(SERIALISED_METADATA)

@patch("toolkits.clients.validation_client.requests.post")
def test_validate_rocrate_metadata_json_error(mock_post):
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.side_effect = requests.exceptions.JSONDecodeError("Expecting value", "", 0)
    mock_post.return_value = mock_response

    with pytest.raises(requests.exceptions.JSONDecodeError, 
                       match="Expecting value: line 1 column 1 \\(char 0\\)"):
        validate_rocrate_metadata(SERIALISED_METADATA)
