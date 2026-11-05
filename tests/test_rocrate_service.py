import pytest
import sys
import shutil
from pathlib import Path
from zipfile import ZipFile

from fivesafe_crate_py import FiveSafesCrate
from rocrate.model import File, ContextEntity, Person


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from toolkits.config.settings import ROCRATE_METADATA_FILENAME, TES_TASK_SCHEMA_ID, TES_TASK_ID_SCHEMA_ID
from toolkits.services.rocrate_service import (
    is_valid_output_rocrate_path,
    get_tes_task_id,
    get_tes_msg_entity,
    create_tes_submission_crate,
    create_tes_result_crate,
    resolve_metadata_path,
    load_rocrate_metadata,
)


FIXTURE_DIRS = [
    Path(__file__).parent / "data" / "embedded-5s-tes-pre-submission",
    Path(__file__).parent / "data" / "5s-tes-pre-submission",
]
FIXTURE_METADATA_PATHS = [dir / ROCRATE_METADATA_FILENAME for dir in FIXTURE_DIRS]
FIXTURE_SUBMISSION_CRATE_PATH = Path(__file__).parent / "data" / "5s-tes-submission" / ROCRATE_METADATA_FILENAME


@pytest.mark.parametrize(
        ("input_filename", "relative_output_path", "valid"),
        [
            (ROCRATE_METADATA_FILENAME, "output", True),
            (ROCRATE_METADATA_FILENAME, "input", False),
            (ROCRATE_METADATA_FILENAME, "input/output", False),
            ("meta.txt", "input", True),
            ("meta.txt", "input/meta.txt/output", False),
            (ROCRATE_METADATA_FILENAME, "output/../input", False),
        ],
        ids=[
            "valid", "invalid_same_dir", "invalid_nested_dir",
            "valid_same_dir_for_non_metadata_file", "invalid_file_as_dir", "invalid_edge_case"
        ]
    )
def test_is_valid_output_rocrate_path_from_file_input(tmp_path, input_filename, relative_output_path, valid):
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    input_path = input_dir / input_filename
    output_path = tmp_path / relative_output_path

    input_path.write_text("{\"name\": \"Hello World\"}")

    assert is_valid_output_rocrate_path(input_path, output_path) is valid

@pytest.mark.parametrize(
        ("relative_output_path", "valid"),
        [
            ("output", True),
            ("input", False),
            ("input/output", False),
            ("output/../input", False),
        ],
        ids=["valid", "invalid_same_dir", "invalid_nested_dir", "invalid_edge_case"]
    )
def test_is_valid_output_rocrate_path_from_dir_input(tmp_path, relative_output_path, valid):
    input_path = tmp_path / "input"
    output_path = tmp_path / relative_output_path

    assert is_valid_output_rocrate_path(input_path, output_path) is valid

@pytest.mark.parametrize(
        ("relative_output_path", "valid"),
        [
            ("output", True),
            ("", True),
            ("input.zip/dir", False),
            ("output/../input.zip", False),
        ],
        ids=["valid", "valid_same_dir", "invalid_nested_dir", "invalid_edge_case"]
    )
def test_is_valid_output_rocrate_path_from_zip_input(tmp_path, relative_output_path, valid):
    input_zip = tmp_path / "input.zip"
    output_path = tmp_path / relative_output_path

    with ZipFile(input_zip, "w") as zip_file:
        zip_file.writestr(ROCRATE_METADATA_FILENAME, "{\"name\": \"Hello World\"}")

    assert is_valid_output_rocrate_path(input_zip, output_path) is valid

def test_get_tes_task_id_valid():
    crate = FiveSafesCrate(FIXTURE_SUBMISSION_CRATE_PATH, version="1.0")

    assert get_tes_task_id(crate) == 1

def test_get_tes_task_id_with_no_id_entity():
    crate = FiveSafesCrate(version="1.0")

    with pytest.raises(ValueError, match="No TES task ID found in RO-Crate metadata."):
        get_tes_task_id(crate)

def test_get_tes_task_id_with_multiple_id_entities():
    crate = FiveSafesCrate(FIXTURE_SUBMISSION_CRATE_PATH, version="1.0")

    entity = crate.get("urn:uuid:1ec84024-798f-47b0-84bc-26a4a603a1ec")
    crate.add(ContextEntity(crate, "#tes-task-id-2", entity.properties()))

    with pytest.raises(ValueError, match="Multiple TES task IDs found in RO-Crate metadata."):
        get_tes_task_id(crate)

def test_get_tes_task_id_with_no_submission_action():
    crate = FiveSafesCrate(FIXTURE_SUBMISSION_CRATE_PATH, version="1.0")
    action = crate.get("urn:uuid:b1563e90-fcdb-4ed5-80fa-21c8ee1d969e")
    crate.delete(action)

    with pytest.raises(ValueError, match="The TES task submission action entity must carry the TES task ID."):
        get_tes_task_id(crate)

@pytest.mark.parametrize("metadata_path", FIXTURE_METADATA_PATHS, ids=lambda val: f"{val.parent.name}")
def test_get_tes_msg_entity_valid(metadata_path):
    crate = FiveSafesCrate(metadata_path, version="1.0")

    assert get_tes_msg_entity(crate).get("conformsTo") == TES_TASK_SCHEMA_ID

def test_get_tes_msg_entity_with_no_id_entity():
    crate = FiveSafesCrate(version="1.0")

    with pytest.raises(ValueError, match="No TES message found in RO-Crate metadata."):
        get_tes_msg_entity(crate)

def test_get_tes_msg_entity_with_multiple_id_entities():
    crate = FiveSafesCrate(version="1.0")

    for i in range(2):
        crate.add(ContextEntity(crate, f"#tes-msg-entity-{i}", properties={
            "@type": "File",
            "conformsTo": {"@id": TES_TASK_SCHEMA_ID},
            "encodingFormat": "application/json"
        }))

    with pytest.raises(ValueError, match="Multiple TES message candidates found in RO-Crate metadata."):
        get_tes_msg_entity(crate)

@pytest.mark.parametrize("metadata_path", FIXTURE_METADATA_PATHS, ids=lambda val: f"{val.parent.name}")
def test_create_tes_submission_crate(metadata_path):
    crate = FiveSafesCrate(metadata_path, version="1.0")
    initial_entities = list(crate.get_entities())

    task_id = "1"
    crate = create_tes_submission_crate(crate, task_id)
    new_entities = [entity for entity in crate.get_entities() if entity not in initial_entities]

    action_exists, task_id_exists = False, False
    for entity in new_entities:
        if "AskAction" in entity.type and "prov:Activity" in entity.type:
            action_exists = True
        if entity.get("propertyID") == TES_TASK_ID_SCHEMA_ID:
            task_id_exists = True
            assert entity.get("value") == task_id

    assert action_exists and task_id_exists
    assert len(new_entities) == 4

def test_create_tes_result_crate(tmp_path):
    crate = FiveSafesCrate(FIXTURE_SUBMISSION_CRATE_PATH, version="1.0")
    initial_entities = list(crate.get_entities())

    output_path = tmp_path / "stdout.txt"
    output_path.write_text("Hello World")

    crate = create_tes_result_crate(crate, {"1": [output_path]}, tmp_path)
    new_entities = [entity for entity in crate.get_entities() if entity not in initial_entities]

    action_exists = False
    for entity in new_entities:
        if "CreateAction" in entity.type and "prov:Activity" in entity.type:
            action_exists = True

    assert action_exists
    assert crate.get("stdout.txt") is not None
    assert len(new_entities) == 2

def test_resolve_metadata_path_rejects_invalid_path(tmp_path, monkeypatch):
    # Mock path which exists but is not dir or file
    crate_dir = tmp_path / "crate"
    crate_dir.mkdir()
    monkeypatch.setattr(
        "toolkits.services.tes_service.Path.is_dir",
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

def test_resolve_metadata_path(tmp_path):
    metadata_path = tmp_path / ROCRATE_METADATA_FILENAME
    metadata_path.write_text("{\"name\": \"Hello World\"}")

    assert resolve_metadata_path(metadata_path) == metadata_path

@pytest.mark.parametrize("dir", FIXTURE_DIRS, ids=lambda val: f"{val.name}")
def test_resolve_metadata_path_accepts_rocrate_directory(tmp_path, dir):
    # A crate directory should resolve to its embedded metadata JSON file.
    crate_dir = tmp_path / "crate"
    shutil.copytree(dir, crate_dir)
    metadata_path = crate_dir / ROCRATE_METADATA_FILENAME

    assert resolve_metadata_path(crate_dir) == metadata_path

@pytest.mark.parametrize("dir", FIXTURE_DIRS, ids=lambda val: f"{val.name}")
def test_load_rocrate_metadata_from_rocrate_directory(tmp_path, dir):
    # Metadata loading should work when the input is the crate root directory.
    crate_dir = tmp_path / "crate"
    shutil.copytree(dir, crate_dir)

    crate_metadata = load_rocrate_metadata(crate_dir)

    assert crate_metadata["@graph"][0]["name"] == "Hello World TES Task"

@pytest.mark.parametrize("metadata_path", FIXTURE_METADATA_PATHS, ids=lambda val: f"{val.parent.name}")
def test_load_rocrate_metadata_from_zip_archive(tmp_path, metadata_path):
    # Metadata loading should also work from a ZIP-packaged RO-Crate.
    archive_path = tmp_path / "crate.zip"
    with ZipFile(archive_path, "w") as zip_file:
        zip_file.write(metadata_path, arcname=ROCRATE_METADATA_FILENAME)

    crate_metadata = load_rocrate_metadata(archive_path)

    assert crate_metadata["@graph"][0]["name"] == "Hello World TES Task"

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
