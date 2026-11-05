import json
import pytest
import sys
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from toolkits.config.settings import ROCRATE_METADATA_FILENAME, TES_TASK_SCHEMA_ID

from toolkits.services.tes_service import (
    conforms_to_tes_task_schema,
    is_creative_work,
    is_file_type,
    is_tes_message_entity,
    load_tes_message,
    extract_or_load_tes_message,
    is_tes_payload,
)


FIXTURE_DIRS = [
    Path(__file__).parent / "data" / "embedded-5s-tes-pre-submission",
    Path(__file__).parent / "data" / "5s-tes-pre-submission",
]
FIXTURE_METADATA_PATHS = [dir / ROCRATE_METADATA_FILENAME for dir in FIXTURE_DIRS]


@pytest.mark.parametrize("metadata_path", FIXTURE_METADATA_PATHS, ids=lambda val: f"{val.parent.parent.name}")
def test_extract_or_load_tes_message_from_fixture(metadata_path):
    # The sample RO-Crate fixtures should yield the embedded or file TES task payload.
    crate_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    tes_message = extract_or_load_tes_message(crate_metadata, metadata_path)

    assert tes_message["name"] == "Hello World"
    assert tes_message["executors"] == [
        {
            "image": "ubuntu", 
            "command": ["echo", "Hello World"],
            "workdir": "/outputs",
            "stdout": "/outputs/stdout"
        }
    ]

@pytest.mark.parametrize(
        "conforms_to",
        [{"@id": TES_TASK_SCHEMA_ID}, TES_TASK_SCHEMA_ID, [{"@id": TES_TASK_SCHEMA_ID}], [TES_TASK_SCHEMA_ID]],
        ids=["dict", "str", "dict_list", "str_list"]
    )
def test_conforms_to_tes_task_schema_accepts_matching_conforms_to(conforms_to):
    entity = {
        "@type": "CreativeWork",
        "conformsTo": conforms_to,
    }

    assert conforms_to_tes_task_schema(entity) is True

@pytest.mark.parametrize(
        ("entity", "valid"),
        [
            ({"@type": "CreativeWork"}, True), 
            ({"@type": ["CreativeWork", "SecondType"]}, True),
            ({"@type": "File"}, False),
            ({"@type": {}}, False),
        ],
        ids=["valid_str", "valid_list", "invalid_str", "invalid_var_type"]
    )
def test_is_creative_work(entity, valid):
    assert is_creative_work(entity) is valid

@pytest.mark.parametrize(
        ("entity", "valid"),
        [
            ({"@type": "File"}, True), 
            ({"@type": ["File", "SecondType"]}, True),
            ({"@type": "CreativeWork"}, False),
            ({"@type": {}}, False),
        ],
        ids=["valid_str", "valid_list", "invalid_str", "invalid_var_type"]
    )
def test_is_file_type(entity, valid):
    assert is_file_type(entity) is valid

@pytest.mark.parametrize(
        ("id", "type", "text", "invalid_metadata"),
        [
            ("#tes-task-1", "CreativeWork", "{}", {"text": {"not": "a string"}}),
            ("tes.json", "File", "null", {"@id": "/absolute/path/to/tes.json"}),
            ("http://localhost:8000/tes.json", "File", "null", {}),
        ],
        ids=["embedded_tes", "file_tes", "web_tes"]
    )
def test_is_tes_message_entity_requires_all_metadata_fields(id, type, text, invalid_metadata):
    entity = {
        "@id": id,
        "@type": type,
        "conformsTo": {"@id": TES_TASK_SCHEMA_ID},
        "encodingFormat": "application/json",
        "text": text,
    }

    assert is_tes_message_entity(entity) is True
    assert is_tes_message_entity({**entity, "encodingFormat": "text/plain"}) is False
    assert is_tes_message_entity({**entity, "@type": "InvalidType"}) is False
    for k, v in invalid_metadata.items():
        assert is_tes_message_entity({**entity, k: v}) is False

def test_is_tes_payload_rejects_non_dict_payload():
    payload = "string"

    assert is_tes_payload(payload) is False

def test_is_tes_payload_rejects_single_executor_object():
    # The shape validator remains strict about TES executor structure.
    payload = {
        "executors": {
            "image": "ubuntu:24.04",
            "command": ["echo", "hello"],
        }
    }

    assert is_tes_payload(payload) is False

@patch("toolkits.services.tes_service.urlopen")
def test_load_tes_message_from_web(mock_urlopen, tmp_path):
    crate_dir = tmp_path / "crate"
    shutil.copytree(FIXTURE_DIRS[1], crate_dir)

    mock_response = MagicMock()
    mock_response.read.return_value = (crate_dir / "tes.json").read_bytes()
    mock_urlopen.return_value.__enter__.return_value = mock_response

    tes_message = load_tes_message(crate_dir, "http://localhost:8000/tes.json")

    assert tes_message["name"] == "Hello World"

@patch("toolkits.services.tes_service.urlopen")
def test_load_tes_message_from_web_failed(mock_urlopen, tmp_path):
    crate_dir = tmp_path / "crate"
    shutil.copytree(FIXTURE_DIRS[1], crate_dir)
    url = "http://localhost:8000/tes.json"

    mock_urlopen.side_effect = HTTPError(url=url, code=404, msg="Not Found", hdrs=None, fp=None)

    with pytest.raises(ValueError, match=f"Unable to load TES message file from: {url}"):
        load_tes_message(crate_dir, url)

def test_load_tes_message_rejects_non_existent_path(tmp_path):
    crate_dir = tmp_path / "crate"

    with pytest.raises(ValueError, match=f"Input path does not exist: {crate_dir}"):
        load_tes_message(crate_dir, "tes.json")

def test_load_tes_message_from_zip_archive(tmp_path):
    archive_path = tmp_path / "crate.zip"
    with ZipFile(archive_path, "w") as zip_file:
        zip_file.writestr("tes.json", "{\"name\": \"Hello World\"}")

    tes_message = load_tes_message(archive_path, "tes.json")

    assert tes_message["name"] == "Hello World"

def test_load_tes_message_rejects_zip_archive_with_no_tes_file(tmp_path):
    archive_path = tmp_path / "crate.zip"
    with ZipFile(archive_path, "w") as zip_file:
        zip_file.writestr("tes.txt", "tes message in text format")

    with pytest.raises(ValueError, match=f"TES message file not found in archive: {archive_path}"):
        load_tes_message(archive_path, "tes.json")

def test_load_tes_message_rejects_invalid_zip_archive(tmp_path):
    archive_path = tmp_path / "crate.zip"
    archive_path.write_bytes(b"file with .zip suffix")

    with pytest.raises(ValueError, match=f"Invalid ZIP archive: {archive_path}"):
        load_tes_message(archive_path, "tes.json")

def test_load_tes_message_rejects_directory_with_no_tes_file(tmp_path):
    crate_dir = tmp_path / "crate"
    crate_dir.mkdir()

    with pytest.raises(ValueError, match=f"TES message file not found at: {crate_dir}"):
        load_tes_message(crate_dir, "tes.json")

def test_load_tes_message_rejects_invalid_path(tmp_path, monkeypatch):
    # Mock path which exists but is not dir or file
    crate_dir = tmp_path / "crate"
    crate_dir.mkdir()
    monkeypatch.setattr(
        "toolkits.services.tes_service.Path.is_dir",
        lambda path: False
    )

    with pytest.raises(ValueError, match=f"Input path is not a file or directory: {crate_dir}"):
        load_tes_message(crate_dir, "tes.json")

def test_extract_or_load_tes_message_rejects_invalid_metadata():
    crate_metadata = {}

    with pytest.raises(ValueError, match="RO-Crate metadata must contain an '@graph' array."):
        extract_or_load_tes_message(crate_metadata, "")

def test_extract_or_load_tes_message_ignores_json_without_tes_conforms_to():
    # JSON text alone must not be mistaken for a TES payload.
    crate_metadata = {
        "@graph": [
            {
                "@id": "#note",
                "@type": "CreativeWork",
                "text": "{\"executors\": [{\"image\": \"alpine\", \"command\": [\"echo\", \"hello\"]}]}",
            }
        ]
    }

    with pytest.raises(ValueError, match="No TES message found"):
        extract_or_load_tes_message(crate_metadata, "")

def test_extract_or_load_tes_message_ignores_multiple_tes_conforms_to():
    crate_metadata = {
        "@graph": [
            {
                "@id": "#tes-task-1",
                "@type": "CreativeWork",
                "conformsTo": {"@id": TES_TASK_SCHEMA_ID},
                "encodingFormat": "application/json",
                "text": "{}",
            },
            {
                "@id": "#tes-task-2",
                "@type": "CreativeWork",
                "conformsTo": {"@id": TES_TASK_SCHEMA_ID},
                "encodingFormat": "application/json",
                "text": "()",
            }
        ]
    }
    with pytest.raises(ValueError, match="Multiple TES message"):
        extract_or_load_tes_message(crate_metadata, "")

def test_extract_or_load_tes_message_ignores_invalid_json_for_tes_conforms_to():
    crate_metadata = {
        "@graph": [
            {
                "@id": "#tes-task-1",
                "@type": "CreativeWork",
                "conformsTo": {"@id": TES_TASK_SCHEMA_ID},
                "encodingFormat": "application/json",
                "text": "not json",
            }
        ]
    }

    with pytest.raises(ValueError, match="not valid JSON"):
        extract_or_load_tes_message(crate_metadata, "")

def test_extract_or_load_tes_message_rejects_invalid_tes_payload_after_selection():
    crate_metadata = {
        "@graph": [
            {
                "@id": "#tes-task-1",
                "@type": "CreativeWork",
                "conformsTo": {"@id": TES_TASK_SCHEMA_ID},
                "encodingFormat": "application/json",
                "text": "{\"executors\": {\"image\": \"alpine\", \"command\": [\"echo\", \"hello\"]}}",
            }
        ]
    }

    with pytest.raises(ValueError, match="not a valid TES payload"):
        extract_or_load_tes_message(crate_metadata, "")
