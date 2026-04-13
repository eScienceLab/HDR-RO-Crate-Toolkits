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
    is_tes_message_entity,
    load_rocrate_metadata,
    extract_tes_message,
    is_tes_payload,
    resolve_metadata_path,
)

from toolkits.scripts.rocrate_to_tes import main


FIXTURE_DIR = (
    Path(__file__).parent
    / "data"
    / "ro-crate_metadata_plus_tes"
    / "five_safes_crate_result"
)
FIXTURE_METADATA_PATH = FIXTURE_DIR / ROCRATE_METADATA_FILENAME


def test_extract_tes_message_from_fixture():
    # The sample RO-Crate fixture should yield the embedded TES task payload.
    crate_metadata = json.loads(FIXTURE_METADATA_PATH.read_text(encoding="utf-8"))

    tes_message = extract_tes_message(crate_metadata)

    assert tes_message["name"] == "Hello World"
    assert tes_message["executors"] == [
        {
            "image": "ubuntu", 
            "command": ["echo", "Hello World"],
            "workdir": "/outputs",
            "stdout": "/outputs/stdout"
        }
    ]


def test_resolve_metadata_path_accepts_rocrate_directory(tmp_path):
    # A crate directory should resolve to its embedded metadata JSON file.
    crate_dir = tmp_path / "crate"
    shutil.copytree(FIXTURE_DIR, crate_dir)
    metadata_path = crate_dir / ROCRATE_METADATA_FILENAME

    assert resolve_metadata_path(crate_dir) == metadata_path


def test_load_rocrate_metadata_from_rocrate_directory(tmp_path):
    # Metadata loading should work when the input is the crate root directory.
    crate_dir = tmp_path / "crate"
    shutil.copytree(FIXTURE_DIR, crate_dir)

    crate_metadata = load_rocrate_metadata(crate_dir)

    assert crate_metadata["@graph"][1]["name"] == "5-Safe RO-Crate Result"


def test_load_rocrate_metadata_from_zip_archive(tmp_path):
    # Metadata loading should also work from a ZIP-packaged RO-Crate.
    archive_path = tmp_path / "crate.zip"
    with ZipFile(archive_path, "w") as zip_file:
        zip_file.write(FIXTURE_METADATA_PATH, arcname=ROCRATE_METADATA_FILENAME)

    crate_metadata = load_rocrate_metadata(archive_path)

    assert crate_metadata["@graph"][1]["name"] == "5-Safe RO-Crate Result"


def test_conforms_to_tes_task_schema_accepts_matching_conforms_to():
    entity = {
        "@type": "CreativeWork",
        "conformsTo": {"@id": TES_TASK_SCHEMA_ID},
    }

    assert conforms_to_tes_task_schema(entity) is True


def test_is_tes_message_entity_requires_all_metadata_fields():
    entity = {
        "@type": "CreativeWork",
        "conformsTo": {"@id": TES_TASK_SCHEMA_ID},
        "encodingFormat": "application/json",
        "text": "{}",
    }

    assert is_tes_message_entity(entity) is True
    assert is_tes_message_entity({**entity, "encodingFormat": "text/plain"}) is False
    assert is_tes_message_entity({**entity, "text": {"not": "a string"}}) is False
    assert is_tes_message_entity({**entity, "@type": "File"}) is False


def test_is_tes_payload_rejects_single_executor_object():
    # The shape validator remains strict about TES executor structure.
    payload = {
        "executors": {
            "image": "ubuntu:24.04",
            "command": ["echo", "hello"],
        }
    }

    assert is_tes_payload(payload) is False


def test_extract_tes_message_ignores_json_without_tes_conforms_to():
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
        extract_tes_message(crate_metadata)


def test_extract_tes_message_ignores_invalid_json_for_tes_conforms_to():
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
        extract_tes_message(crate_metadata)


def test_extract_tes_message_rejects_invalid_tes_payload_after_selection():
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
        extract_tes_message(crate_metadata)


def test_main_prints_extracted_message(capsys):
    # The CLI should emit the extracted TES message as JSON on stdout.
    exit_code = main([str(FIXTURE_METADATA_PATH)])

    captured = capsys.readouterr()
    output = json.loads(captured.out)

    assert exit_code == 0
    assert output["name"] == "Hello world"
    assert output["executors"][0]["image"] == "alpine"


def test_main_accepts_rocrate_directory(tmp_path, capsys):
    # The CLI should also work when pointed at the root directory of a crate.
    crate_dir = tmp_path / "crate"
    shutil.copytree(FIXTURE_DIR, crate_dir)

    exit_code = main([str(crate_dir)])

    captured = capsys.readouterr()
    output = json.loads(captured.out)

    assert exit_code == 0
    assert output["name"] == "Hello world"


def test_main_accepts_rocrate_zip_archive(tmp_path, capsys):
    # The CLI should also work when pointed at a ZIP-packaged RO-Crate.
    archive_path = tmp_path / "crate.zip"
    with ZipFile(archive_path, "w") as zip_file:
        zip_file.write(FIXTURE_METADATA_PATH, arcname=ROCRATE_METADATA_FILENAME)

    exit_code = main([str(archive_path)])

    captured = capsys.readouterr()
    output = json.loads(captured.out)

    assert exit_code == 0
    assert output["name"] == "Hello world"
