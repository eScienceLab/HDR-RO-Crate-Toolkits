import pytest
import sys
import shutil
from pathlib import Path
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from toolkits.config.settings import ROCRATE_METADATA_FILENAME
from toolkits.scripts.rocrate_to_tes import main


FIXTURE_DIRS = [
    Path(__file__).parent / "data" / "embedded-5s-tes-pre-submission",
    Path(__file__).parent / "data" / "5s-tes-pre-submission",
]
FIXTURE_METADATA_PATHS = [dir / ROCRATE_METADATA_FILENAME for dir in FIXTURE_DIRS]


@pytest.fixture
def mock_clients(monkeypatch):
    monkeypatch.setattr(
        "toolkits.scripts.rocrate_to_tes.is_rocrate_metadata_valid",
        lambda data: True
    )
    monkeypatch.setattr(
        "toolkits.scripts.rocrate_to_tes.Workbench.submit",
        lambda data: 1
    )
    yield

@pytest.fixture
def mock_wb_config(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(
        """
        config:
          project: "Testing"
          tes_base_url: "https://submission.layer.api"
          tres:
            - "DEMO"
        auth:
          access_token: "SECRET"
        """
    )
    return str(path)

@pytest.mark.parametrize("metadata_path", FIXTURE_METADATA_PATHS, ids=lambda val: f"{val.parent.parent.name}")
def test_main_prints_extracted_message(tmp_path, capsys, mock_wb_config, mock_clients, metadata_path):
    # The CLI should emit the extracted TES message as JSON on stdout.
    exit_code = main([str(metadata_path), "--config_path", mock_wb_config, "--output_rocrate", str(tmp_path / "output-crate"), "-v"])

    captured = capsys.readouterr()
    output = captured.out

    assert exit_code == 0
    assert '"name": "Hello World"' in output
    assert  '"executors": [\n    {\n      "image": "ubuntu"' in output

@pytest.mark.parametrize("metadata_path", FIXTURE_METADATA_PATHS, ids=lambda val: f"{val.parent.parent.name}")
def test_main_less_verbose(tmp_path, capsys, mock_wb_config, mock_clients, metadata_path):
    exit_code = main([str(metadata_path), "--config_path", mock_wb_config, "--output_rocrate", str(tmp_path / "output-crate")])

    captured = capsys.readouterr()
    output = captured.out

    assert exit_code == 0
    assert '"name": "Hello World"' not in output
    assert  "RO-Crate metadata validation successful" in output
    assert  "Submitted task ID: 1" in output

@pytest.mark.parametrize("metadata_path", FIXTURE_METADATA_PATHS, ids=lambda val: f"{val.parent.parent.name}")
def test_main_no_roc_validation(tmp_path, capsys, mock_wb_config, mock_clients, metadata_path):
    exit_code = main([str(metadata_path), "--config_path", mock_wb_config, "--output_rocrate", str(tmp_path / "output-crate"), "--disable_roc_validator"])

    captured = capsys.readouterr()
    output = captured.out

    assert exit_code == 0
    assert  "RO-Crate metadata validation successful" not in output
    assert  "Submitted task ID: 1" in output

@pytest.mark.parametrize("dir", FIXTURE_DIRS, ids=lambda val: f"{val.parent.name}")
def test_main_accepts_rocrate_directory(tmp_path, capsys, mock_wb_config, mock_clients, dir):
    # The CLI should also work when pointed at the root directory of a crate.
    crate_dir = tmp_path / "crate"
    shutil.copytree(dir, crate_dir)

    exit_code = main([str(crate_dir), "--config_path", mock_wb_config, "--output_rocrate", str(tmp_path / "output-crate"), "-v"])

    captured = capsys.readouterr()
    output = captured.out

    assert exit_code == 0
    assert '"name": "Hello World"' in output

@pytest.mark.parametrize("dir", FIXTURE_DIRS, ids=lambda val: f"{val.parent.name}")
def test_main_accepts_rocrate_zip_archive(tmp_path, capsys, mock_wb_config, mock_clients, dir):
    # The CLI should also work when pointed at a ZIP-packaged RO-Crate.
    archive_path = tmp_path / "crate.zip"
    with ZipFile(archive_path, "w") as zip_file:
        for file in dir.rglob("*"):
            if file.is_file():
                zip_file.write(file, arcname=file.relative_to(dir))

    exit_code = main([str(archive_path), "--config_path", mock_wb_config, "--output_rocrate", str(tmp_path / "output-crate"), "-v"])

    captured = capsys.readouterr()
    output = captured.out

    assert exit_code == 0
    assert '"name": "Hello World"' in output
