import json
from pathlib import Path
import sys
import shutil
from zipfile import ZipFile

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from toolkits.config.settings import ROCRATE_METADATA_FILENAME, TES_TASK_SCHEMA_ID

from toolkits.clients.tes_client import (
    conforms_to_tes_task_schema,
    is_creative_work,
    is_file_type,
    is_tes_message_entity,
    load_rocrate_metadata,
    extract_or_load_tes_message,
    is_tes_payload,
    resolve_metadata_path,
)

from toolkits.scripts.rocrate_to_tes import main


FIXTURE_DIRS = [
    Path(__file__).parent / "data" / "ro-crate_metadata_plus_tes" / "five_safes_crate_result",
    Path(__file__).parent / "data" / "ro-crate_metadata_plus_file_tes" / "five_safes_crate_result",
]
FIXTURE_METADATA_PATHS = [dir / ROCRATE_METADATA_FILENAME for dir in FIXTURE_DIRS]


@pytest.fixture
def mock_clients(monkeypatch):
    monkeypatch.setattr(
        "toolkits.scripts.rocrate_to_tes.is_rocrate_metadata_valid",
        lambda data: True
    )
    monkeypatch.setattr(
        "toolkits.scripts.rocrate_to_tes.create_tes_task",
        lambda data: {"$id": "1", "id": "1"}
    )
    yield


@pytest.mark.parametrize("metadata_path", FIXTURE_METADATA_PATHS, ids=lambda val: f"{val.parent.parent.name}")
def test_extract_or_load_tes_message_from_fixture(metadata_path):
    # The sample RO-Crate fixture should yield the embedded TES task payload.
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


def test_resolve_metadata_path_rejects_invalid_path(tmp_path, monkeypatch):
    # Mock path which exists but is not dir or file
    crate_dir = tmp_path / "crate"
    crate_dir.mkdir()
    monkeypatch.setattr(
        "toolkits.clients.tes_client.Path.is_dir",
        lambda path: False
    )

    with pytest.raises(ValueError, match=f"Input path is not a file or directory: {crate_dir}"):
        resolve_metadata_path(crate_dir)


def test_resolve_metadata_path_rejects_non_existent_path(tmp_path):
    crate_dir = tmp_path / "crate"

    with pytest.raises(ValueError, match=f"Input path does not exist: {crate_dir}"):
        resolve_metadata_path(crate_dir)


def test_resolve_metadata_path_rejects_directory_with_no_metadata(tmp_path):
    crate_dir = tmp_path / "crate"
    crate_dir.mkdir()

    with pytest.raises(ValueError, match=f"RO-Crate metadata file not found at: {crate_dir}"):
        resolve_metadata_path(crate_dir)


@pytest.mark.parametrize("dir", FIXTURE_DIRS, ids=lambda val: f"{val.parent.name}")
def test_resolve_metadata_path_accepts_rocrate_directory(tmp_path, dir):
    # A crate directory should resolve to its embedded metadata JSON file.
    crate_dir = tmp_path / "crate"
    shutil.copytree(dir, crate_dir)
    metadata_path = crate_dir / ROCRATE_METADATA_FILENAME

    assert resolve_metadata_path(crate_dir) == metadata_path


@pytest.mark.parametrize("dir", FIXTURE_DIRS, ids=lambda val: f"{val.parent.name}")
def test_load_rocrate_metadata_from_rocrate_directory(tmp_path, dir):
    # Metadata loading should work when the input is the crate root directory.
    crate_dir = tmp_path / "crate"
    shutil.copytree(dir, crate_dir)

    crate_metadata = load_rocrate_metadata(crate_dir)

    assert crate_metadata["@graph"][1]["name"] == "5-Safe RO-Crate Result"


@pytest.mark.parametrize("metadata_path", FIXTURE_METADATA_PATHS, ids=lambda val: f"{val.parent.parent.name}")
def test_load_rocrate_metadata_from_zip_archive(tmp_path, metadata_path):
    # Metadata loading should also work from a ZIP-packaged RO-Crate.
    archive_path = tmp_path / "crate.zip"
    with ZipFile(archive_path, "w") as zip_file:
        zip_file.write(metadata_path, arcname=ROCRATE_METADATA_FILENAME)

    crate_metadata = load_rocrate_metadata(archive_path)

    assert crate_metadata["@graph"][1]["name"] == "5-Safe RO-Crate Result"


def test_load_rocrate_metadata_rejects_zip_archive_with_no_metadata(tmp_path):
    archive_path = tmp_path / "crate.zip"
    with ZipFile(archive_path, "w") as zip_file:
        zip_file.writestr("ro-crate-metadata.txt", "metadata in text format")

    with pytest.raises(ValueError, match=f"RO-Crate metadata file not found in archive: {archive_path}"):
        load_rocrate_metadata(archive_path)


def test_load_rocrate_metadata_rejects_invalid_zip_archive(tmp_path):
    archive_path = tmp_path / "crate.zip"
    archive_path.write_bytes(b"file with .zip suffix")

    with pytest.raises(ValueError, match=f"Invalid ZIP archive: {archive_path}"):
        load_rocrate_metadata(archive_path)


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


@pytest.mark.parametrize("metadata_path", FIXTURE_METADATA_PATHS, ids=lambda val: f"{val.parent.parent.name}")
def test_main_prints_extracted_message(capsys, mock_clients, metadata_path):
    # The CLI should emit the extracted TES message as JSON on stdout.
    exit_code = main([str(metadata_path)])

    captured = capsys.readouterr()
    output = captured.out

    assert exit_code == 0
    assert '"name": "Hello World"' in output
    assert  '"executors": [\n    {\n      "image": "ubuntu"' in output


@pytest.mark.parametrize("dir", FIXTURE_DIRS, ids=lambda val: f"{val.parent.name}")
def test_main_accepts_rocrate_directory(tmp_path, capsys, mock_clients, dir):
    # The CLI should also work when pointed at the root directory of a crate.
    crate_dir = tmp_path / "crate"
    shutil.copytree(dir, crate_dir)

    exit_code = main([str(crate_dir)])

    captured = capsys.readouterr()
    output = captured.out

    assert exit_code == 0
    assert '"name": "Hello World"' in output


@pytest.mark.parametrize("dir", FIXTURE_DIRS, ids=lambda val: f"{val.parent.name}")
def test_main_accepts_rocrate_zip_archive(tmp_path, capsys, mock_clients, dir):
    # The CLI should also work when pointed at a ZIP-packaged RO-Crate.
    archive_path = tmp_path / "crate.zip"
    with ZipFile(archive_path, "w") as zip_file:
        for file in dir.rglob("*"):
            if file.is_file():
                zip_file.write(file, arcname=file.relative_to(dir))

    exit_code = main([str(archive_path)])

    captured = capsys.readouterr()
    output = captured.out

    assert exit_code == 0
    assert '"name": "Hello World"' in output
