import pytest

from toolkits.services.validation_service import is_rocrate_metadata_valid


def test_is_rocrate_metadata_valid_true(monkeypatch):
    monkeypatch.setattr(
        "toolkits.services.validation_service.validate_rocrate_metadata",
        lambda data: {'result': '{\n    "passed": true,\n    "issues": []\n}'}
    )

    assert is_rocrate_metadata_valid({}) is True

def test_is_rocrate_metadata_valid_false(monkeypatch):
    monkeypatch.setattr(
        "toolkits.services.validation_service.validate_rocrate_metadata",
        lambda data: {'result': '{\n    "passed": false,\n    "issues": []\n}'}
    )

    assert is_rocrate_metadata_valid({}) is False

def test_is_rocrate_metadata_valid_missing_result(monkeypatch):
    monkeypatch.setattr(
        "toolkits.services.validation_service.validate_rocrate_metadata",
        lambda data: {}
    )

    assert is_rocrate_metadata_valid({}) is False

def test_is_rocrate_metadata_valid_invalid_json(monkeypatch):
    monkeypatch.setattr(
        "toolkits.services.validation_service.validate_rocrate_metadata",
        lambda data: {'result': '{invalid}'}
    )

    assert is_rocrate_metadata_valid({}) is False

def test_is_rocrate_metadata_valid_missing_passed(monkeypatch):
    monkeypatch.setattr(
        "toolkits.services.validation_service.validate_rocrate_metadata",
        lambda data: {'result': '{\n    "issues": []\n}'}
    )

    assert is_rocrate_metadata_valid({}) is False