import pytest

from unittest.mock import Mock, patch

from toolkits.services.validation_service import is_rocrate_metadata_valid


CRATE_METADATA = {"@context": "https://w3id.org/ro/crate/1.2/context"}

@patch("toolkits.services.validation_service.validate_rocrate_metadata")
def test_is_rocrate_metadata_valid_true(mock_client):
    mock_client.return_value = {'result': '{\n    "passed": true,\n    "issues": []\n}'}
    assert is_rocrate_metadata_valid(CRATE_METADATA) is True

@patch("toolkits.services.validation_service.validate_rocrate_metadata")
def test_is_rocrate_metadata_valid_false(mock_client):
    mock_client.return_value = {'result': '{\n    "passed": false,\n    "issues": []\n}'}
    assert is_rocrate_metadata_valid(CRATE_METADATA) is False

def test_validate_rocrate_metadata_non_dict_input():
    with pytest.raises(TypeError, match="crate_metadata must be a dictionary"):
        is_rocrate_metadata_valid("not dict")

@patch("toolkits.services.validation_service.validate_rocrate_metadata")
def test_is_rocrate_metadata_valid_missing_result(mock_client):
    mock_client.return_value = {}
    assert is_rocrate_metadata_valid(CRATE_METADATA) is False

@patch("toolkits.services.validation_service.validate_rocrate_metadata")
def test_is_rocrate_metadata_valid_invalid_json_in_result(mock_client):
    mock_client.return_value = {'result': '{invalid}'}
    with pytest.raises(ValueError, match="Invalid JSON in 'result'"):
        is_rocrate_metadata_valid(CRATE_METADATA) is False

@patch("toolkits.services.validation_service.validate_rocrate_metadata")
def test_is_rocrate_metadata_valid_missing_passed(mock_client):
    mock_client.return_value = {'result': '{\n    "issues": []\n}'}
    assert is_rocrate_metadata_valid(CRATE_METADATA) is False