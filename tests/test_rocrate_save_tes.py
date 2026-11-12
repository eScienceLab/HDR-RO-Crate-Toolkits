import pytest
import sys
import shutil
from pathlib import Path
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from toolkits.config.settings import ROCRATE_METADATA_FILENAME
from toolkits.scripts.rocrate_save_tes import main


FIXTURE_DIR = Path(__file__).parent / "data" / "5s-tes-submission"
FIXTURE_METADATA_PATHS = FIXTURE_DIR / ROCRATE_METADATA_FILENAME


@pytest.fixture
def mock_clients(monkeypatch, tmp_path):
    def mock_fetch_outputs(self, task_id, output_dir):
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / "stdout"
        output_file.write_text("Hello World")

        return {"stdout": [output_file]}

    monkeypatch.setattr(
        "toolkits.scripts.rocrate_save_tes.Workbench.fetch_outputs",
        mock_fetch_outputs,
    )
    yield

def test_main_creates_result_rocrate(tmp_path, capsys, mock_wb_config, mock_clients):
    output_dir = tmp_path / "tes-result-ro-crate"
    exit_code = main([str(FIXTURE_METADATA_PATHS), "--config_path", mock_wb_config, "--output_rocrate", str(output_dir)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "RO-Crate loaded" in captured.out
    assert f"RO-Crate tes-result-ro-crate created at {tmp_path}" in captured.out
    assert output_dir.exists()
    assert (output_dir / ROCRATE_METADATA_FILENAME).exists()

# TODO: Add this test if logger.debug() is used in the future
# def test_main_more_verbose(tmp_path, capsys, mock_wb_config, mock_clients):
#     assert exit_code == 0
#     assert "DEBUG" in output

def test_main_no_outputs(tmp_path, capsys, mock_wb_config, monkeypatch):
    output_dir = tmp_path / "tes-result-ro-crate"
    monkeypatch.setattr(
        "toolkits.scripts.rocrate_save_tes.Workbench.fetch_outputs",
        lambda self, task_id, output_dir: {},
    )

    exit_code = main([str(FIXTURE_METADATA_PATHS), "--config_path", mock_wb_config, "--output_rocrate", str(output_dir)])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "TES task has no outputs; result RO-Crate was not created." in captured.err

def test_main_accepts_rocrate_directory(tmp_path, capsys, mock_wb_config, mock_clients):
    output_dir = tmp_path / "tes-result-ro-crate"
    exit_code = main([str(FIXTURE_DIR), "--config_path", mock_wb_config, "--output_rocrate", str(output_dir)])

    captured = capsys.readouterr()
    
    assert exit_code == 0
    assert f"RO-Crate tes-result-ro-crate created at {tmp_path}" in captured.out
    assert (tmp_path / "tes-result-ro-crate" / ROCRATE_METADATA_FILENAME).exists()

def test_main_accepts_rocrate_zip_archive(tmp_path, capsys, mock_wb_config, mock_clients):
    output_dir = tmp_path / "tes-result-ro-crate"
    archive_path = tmp_path / "crate.zip"
    with ZipFile(archive_path, "w") as zip_file:
        for file in FIXTURE_DIR.rglob("*"):
            if file.is_file():
                zip_file.write(file, arcname=file.relative_to(FIXTURE_DIR))

    exit_code = main([str(archive_path), "--config_path", mock_wb_config, "--output_rocrate", str(output_dir)])

    captured = capsys.readouterr()
    
    assert exit_code == 0
    assert f"RO-Crate tes-result-ro-crate created at {tmp_path}" in captured.out
    assert (tmp_path / "tes-result-ro-crate" / ROCRATE_METADATA_FILENAME).exists()
