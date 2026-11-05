import pytest
import sys
import shutil
from pathlib import Path
from zipfile import ZipFile


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from toolkits.config.settings import ROCRATE_METADATA_FILENAME
from toolkits.services.rocrate_service import load_rocrate_metadata, resolve_metadata_path


FIXTURE_DIRS = [
    Path(__file__).parent / "data" / "embedded-5s-tes-pre-submission",
    Path(__file__).parent / "data" / "5s-tes-pre-submission",
]
FIXTURE_METADATA_PATHS = [dir / ROCRATE_METADATA_FILENAME for dir in FIXTURE_DIRS]


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
