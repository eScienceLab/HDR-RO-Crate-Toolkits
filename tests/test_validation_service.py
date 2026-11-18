import pytest

from unittest.mock import patch

from toolkits.services.validation_service import is_rocrate_metadata_valid


CRATE_METADATA = {"@context": "https://w3id.org/ro/crate/1.2/context"}

# Response bodies in the form returned by the RO-Crate Validation Service 2.x
VALID_RESPONSE = {
    "status": "valid",
    "profile": None,
    "created_at": None,
    "detail": {"passed": True, "issues": []},
}
INVALID_RESPONSE = {
    "status": "invalid",
    "profile": None,
    "created_at": None,
    "detail": {"passed": False, "issues": [{"message": "Missing datePublished"}]},
}
ERROR_RESPONSE = {
    "status": "error",
    "profile": None,
    "created_at": None,
    "error": "Profile not found",
}

@patch("toolkits.services.validation_service.validate_rocrate_metadata")
def test_is_rocrate_metadata_valid_true(mock_client):
    mock_client.return_value = VALID_RESPONSE
    assert is_rocrate_metadata_valid(CRATE_METADATA) is True

@patch("toolkits.services.validation_service.validate_rocrate_metadata")
def test_is_rocrate_metadata_valid_false(mock_client):
    mock_client.return_value = INVALID_RESPONSE
    assert is_rocrate_metadata_valid(CRATE_METADATA) is False

def test_validate_rocrate_metadata_non_dict_input():
    with pytest.raises(TypeError, match="crate_metadata must be a dictionary"):
        is_rocrate_metadata_valid("not dict")

@patch("toolkits.services.validation_service.validate_rocrate_metadata")
def test_is_rocrate_metadata_valid_error_status(mock_client):
    mock_client.return_value = ERROR_RESPONSE
    with pytest.raises(ValueError, match="'error' \\(Profile not found\\)"):
        is_rocrate_metadata_valid(CRATE_METADATA)

@patch("toolkits.services.validation_service.validate_rocrate_metadata")
def test_is_rocrate_metadata_valid_missing_status(mock_client):
    mock_client.return_value = {}
    with pytest.raises(ValueError, match="Unexpected validation status: None"):
        is_rocrate_metadata_valid(CRATE_METADATA)

@patch("toolkits.services.validation_service.validate_rocrate_metadata")
def test_is_rocrate_metadata_valid_old_response_format(mock_client):
    # Responses from versions before 2.0 have no `status`, so they are rejected
    # instead of being treated as a failed validation.
    mock_client.return_value = {'result': '{\n    "passed": true,\n    "issues": []\n}'}
    with pytest.raises(ValueError, match="Unexpected validation status"):
        is_rocrate_metadata_valid(CRATE_METADATA)
