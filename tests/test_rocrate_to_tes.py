import pytest
import sys
import shutil
from pathlib import Path
from zipfile import ZipFile
import requests
from five_safes_tes_workbench.common.exceptions.submission_errors import SubmissionError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from toolkits.config.settings import ROCRATE_METADATA_FILENAME
from toolkits.config.exit_codes import ExitCode
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


@pytest.mark.parametrize("metadata_path", FIXTURE_METADATA_PATHS, ids=lambda val: f"{val.parent.name}")
def test_main_prints_extracted_message(tmp_path, capsys, mock_wb_config, mock_clients, metadata_path):
    # The CLI should emit the extracted TES message as JSON on stdout.
    exit_code = main([str(metadata_path), "--config_path", mock_wb_config, "--output_rocrate", str(tmp_path / "output-crate"), "-v"])

    captured = capsys.readouterr()
    output = captured.out

    assert exit_code == 0
    assert '"name": "Hello World"' in output
    assert "DEBUG" in output
    assert '"executors": [\n    {\n      "image": "ubuntu"' in output

@pytest.mark.parametrize("metadata_path", FIXTURE_METADATA_PATHS, ids=lambda val: f"{val.parent.name}")
def test_main_less_verbose(tmp_path, capsys, mock_wb_config, mock_clients, metadata_path):
    exit_code = main([str(metadata_path), "--config_path", mock_wb_config, "--output_rocrate", str(tmp_path / "output-crate")])

    captured = capsys.readouterr()
    output = captured.out

    assert exit_code == 0
    assert "DEBUG" not in output
    assert "RO-Crate metadata validation successful" in output
    assert "Submitted task ID: 1" in output

@pytest.mark.parametrize("metadata_path", FIXTURE_METADATA_PATHS, ids=lambda val: f"{val.parent.name}")
def test_main_quiet(tmp_path, capsys, mock_wb_config, mock_clients, metadata_path):
    exit_code = main([str(metadata_path), "--config_path", mock_wb_config, "--output_rocrate", str(tmp_path / "output-crate"), "-q"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == ""
    assert captured.err == ""

def test_main_rejects_quiet_with_verbose(tmp_path, mock_wb_config):
    with pytest.raises(SystemExit) as exc_info:
        main([str(FIXTURE_METADATA_PATHS[0]), "--config_path", mock_wb_config, "-q", "-v"])

    assert exc_info.value.code == 2

@pytest.mark.parametrize("metadata_path", FIXTURE_METADATA_PATHS, ids=lambda val: f"{val.parent.name}")
def test_main_no_roc_validation(tmp_path, capsys, mock_wb_config, mock_clients, metadata_path):
    exit_code = main([str(metadata_path), "--config_path", mock_wb_config, "--output_rocrate", str(tmp_path / "output-crate"), "--disable_roc_validator"])

    captured = capsys.readouterr()
    output = captured.out

    assert exit_code == 0
    assert "RO-Crate metadata validation successful" not in output
    assert "Submitted task ID: 1" in output

@pytest.mark.parametrize("dir", FIXTURE_DIRS, ids=lambda val: f"{val.name}")
def test_main_accepts_rocrate_directory(tmp_path, capsys, mock_wb_config, mock_clients, dir):
    # The CLI should also work when pointed at the root directory of a crate.
    crate_dir = tmp_path / "crate"
    shutil.copytree(dir, crate_dir)

    exit_code = main([str(crate_dir), "--config_path", mock_wb_config, "--output_rocrate", str(tmp_path / "output-crate"), "-v"])

    captured = capsys.readouterr()
    output = captured.out

    assert exit_code == 0
    assert '"name": "Hello World"' in output

@pytest.mark.parametrize("dir", FIXTURE_DIRS, ids=lambda val: f"{val.name}")
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


# ----- Exit codes -----

def _run_main(input_path, config_path, output_path):
    return main([str(input_path), "--config_path", str(config_path), "--output_rocrate", str(output_path)])


def test_main_missing_input_returns_input_error(tmp_path, mock_wb_config, mock_clients):
    exit_code = _run_main(tmp_path / "missing-crate", mock_wb_config, tmp_path / "output-crate")

    assert exit_code == ExitCode.INPUT_ERROR


def test_main_missing_referenced_tes_file_returns_input_error(tmp_path, capsys, mock_wb_config, mock_clients):
    # A metadata file path whose referenced tes.json is missing should not crash with a traceback.
    crate_dir = tmp_path / "crate"
    shutil.copytree(FIXTURE_DIRS[1], crate_dir)
    (crate_dir / "tes.json").unlink()

    exit_code = _run_main(crate_dir / ROCRATE_METADATA_FILENAME, mock_wb_config, tmp_path / "output-crate")

    assert exit_code == ExitCode.INPUT_ERROR
    assert "tes.json" in capsys.readouterr().err


def test_main_nested_output_returns_output_error(tmp_path, mock_wb_config, mock_clients):
    crate_dir = tmp_path / "crate"
    shutil.copytree(FIXTURE_DIRS[0], crate_dir)

    exit_code = _run_main(crate_dir, mock_wb_config, crate_dir / "output-crate")

    assert exit_code == ExitCode.OUTPUT_ERROR


def test_main_invalid_metadata_returns_validation_failed(tmp_path, mock_wb_config, mock_clients, monkeypatch):
    monkeypatch.setattr("toolkits.scripts.rocrate_to_tes.is_rocrate_metadata_valid", lambda data: False)

    exit_code = _run_main(FIXTURE_METADATA_PATHS[0], mock_wb_config, tmp_path / "output-crate")

    assert exit_code == ExitCode.VALIDATION_FAILED


def test_main_validator_unreachable_returns_service_error(tmp_path, mock_wb_config, mock_clients, monkeypatch):
    def raise_connection_error(data):
        raise requests.exceptions.ConnectionError("validator down")
    monkeypatch.setattr("toolkits.scripts.rocrate_to_tes.is_rocrate_metadata_valid", raise_connection_error)

    exit_code = _run_main(FIXTURE_METADATA_PATHS[0], mock_wb_config, tmp_path / "output-crate")

    assert exit_code == ExitCode.SERVICE_ERROR


@pytest.mark.parametrize(
    "config_content",
    [None, "config: [unclosed", "config:\n  project: Testing\n"],
    ids=["missing_file", "invalid_yaml", "schema_invalid"],
)
def test_main_bad_workbench_config_returns_input_error(tmp_path, mock_clients, config_content):
    config_path = tmp_path / "config.yaml"
    if config_content is not None:
        config_path.write_text(config_content)

    exit_code = _run_main(FIXTURE_METADATA_PATHS[0], config_path, tmp_path / "output-crate")

    assert exit_code == ExitCode.INPUT_ERROR


def test_main_submission_failure_returns_service_error(tmp_path, mock_wb_config, mock_clients, monkeypatch):
    def raise_submission_error(self):
        raise SubmissionError("TES endpoint unavailable", status_code=503)
    monkeypatch.setattr("toolkits.scripts.rocrate_to_tes.Workbench.submit", raise_submission_error)

    exit_code = _run_main(FIXTURE_METADATA_PATHS[0], mock_wb_config, tmp_path / "output-crate")

    assert exit_code == ExitCode.SERVICE_ERROR


def test_main_workbench_rejected_config_returns_input_error(tmp_path, mock_clients, invalid_wb_config):
    exit_code = _run_main(FIXTURE_METADATA_PATHS[0], invalid_wb_config, tmp_path / "output-crate")

    assert exit_code == ExitCode.INPUT_ERROR


def test_main_write_failure_returns_output_error(tmp_path, mock_wb_config, mock_clients, monkeypatch):
    def raise_os_error(self, path):
        raise OSError("disk full")
    monkeypatch.setattr("fivesafe_crate_py.FiveSafesCrate.write", raise_os_error)

    exit_code = _run_main(FIXTURE_METADATA_PATHS[0], mock_wb_config, tmp_path / "output-crate")

    assert exit_code == ExitCode.OUTPUT_ERROR


def test_main_write_failure_reports_submitted_task_id_in_quiet_mode(tmp_path, capsys, mock_wb_config, mock_clients, monkeypatch):
    # The task has already been submitted, so its ID must be visible even with -q,
    # otherwise the user can't fetch its results and may submit it again.
    def raise_os_error(self, path):
        raise PermissionError("Permission denied")
    monkeypatch.setattr("fivesafe_crate_py.FiveSafesCrate.write", raise_os_error)

    exit_code = main([
        str(FIXTURE_METADATA_PATHS[0]), "--config_path", mock_wb_config,
        "--output_rocrate", str(tmp_path / "output-crate"), "-q",
    ])

    captured = capsys.readouterr()
    assert exit_code == ExitCode.OUTPUT_ERROR
    assert "TES task 1 was submitted" in captured.err
