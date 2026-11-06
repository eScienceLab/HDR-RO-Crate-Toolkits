import logging
import shutil
from pathlib import Path

import pytest
import requests
from botocore.exceptions import ClientError

from toolkits.config.exit_codes import ExitCode
from toolkits.scripts.rocrate_save_tes import main


SUBMISSION_CRATE_DIR = Path(__file__).parent / "data" / "5s-tes-submission"
RESULT_FILE = Path(__file__).parent / "data" / "5s-tes-result" / "stdout"


@pytest.fixture
def submission_crate(tmp_path):
    crate_dir = tmp_path / "submission-crate"
    shutil.copytree(SUBMISSION_CRATE_DIR, crate_dir)
    return crate_dir


def _mock_fetch_outputs(monkeypatch, fn):
    monkeypatch.setattr("toolkits.scripts.rocrate_save_tes.Workbench.fetch_outputs", fn)


def _run_main(input_path, config_path, output_dir):
    return main([str(input_path), "--config_path", str(config_path), "--output_dir", str(output_dir)])


def test_main_success(tmp_path, submission_crate, mock_wb_config, monkeypatch):
    def fake_fetch(self, task_id, output_dir):
        output_dir.mkdir(parents=True, exist_ok=True)
        result = output_dir / "stdout"
        shutil.copy(RESULT_FILE, result)
        return {"DEMO": [result]}
    _mock_fetch_outputs(monkeypatch, fake_fetch)

    exit_code = _run_main(submission_crate, mock_wb_config, tmp_path / "out")

    assert exit_code == ExitCode.SUCCESS
    assert (tmp_path / "out" / "tes-result-ro-crate" / "ro-crate-metadata.json").exists()


def test_main_quiet_logs_only_errors(tmp_path, capsys, mock_wb_config):
    exit_code = main([str(tmp_path / "missing-crate"), "--config_path", str(mock_wb_config), "-q"])

    captured = capsys.readouterr()

    assert exit_code == ExitCode.INPUT_ERROR
    assert captured.out == ""
    assert "ERROR" in captured.err


def test_main_rejects_quiet_with_verbose(tmp_path, submission_crate, mock_wb_config):
    with pytest.raises(SystemExit) as exc_info:
        main([str(submission_crate), "--config_path", str(mock_wb_config), "-q", "-v"])

    assert exc_info.value.code == ExitCode.USAGE_ERROR


def test_main_missing_input_returns_input_error(tmp_path, mock_wb_config):
    exit_code = _run_main(tmp_path / "missing-crate", mock_wb_config, tmp_path / "out")

    assert exit_code == ExitCode.INPUT_ERROR


def test_main_workbench_rejected_config_returns_input_error(tmp_path, submission_crate, invalid_wb_config):
    exit_code = _run_main(submission_crate, invalid_wb_config, tmp_path / "out")

    assert exit_code == ExitCode.INPUT_ERROR


def test_main_missing_workbench_config_returns_input_error(tmp_path, submission_crate):
    exit_code = _run_main(submission_crate, tmp_path / "missing.yaml", tmp_path / "out")

    assert exit_code == ExitCode.INPUT_ERROR


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("Child task not found"),
        ValueError("No project S3 info found"),
        ClientError({"Error": {"Code": "AccessDenied"}}, "GetObject"),
        requests.ConnectionError("Connection refused"),
        ConnectionResetError("Connection reset by peer"),
        TimeoutError("timed out"),
    ],
    ids=[
        "runtime_error", "value_error", "s3_client_error", "requests_connection_error",
        "connection_reset", "timeout",
    ],
)
def test_main_fetch_failure_returns_service_error(tmp_path, submission_crate, mock_wb_config, monkeypatch, error):
    def fake_fetch(self, task_id, output_dir):
        raise error
    _mock_fetch_outputs(monkeypatch, fake_fetch)

    exit_code = _run_main(submission_crate, mock_wb_config, tmp_path / "out")

    assert exit_code == ExitCode.SERVICE_ERROR


@pytest.mark.parametrize(
    "error",
    [PermissionError("Permission denied"), OSError(28, "No space left on device")],
    ids=["permission_denied", "disk_full"],
)
def test_main_local_fetch_write_failure_returns_output_error(tmp_path, submission_crate, mock_wb_config, monkeypatch, error):
    def fake_fetch(self, task_id, output_dir):
        raise error
    _mock_fetch_outputs(monkeypatch, fake_fetch)

    exit_code = _run_main(submission_crate, mock_wb_config, tmp_path / "out")

    assert exit_code == ExitCode.OUTPUT_ERROR


def test_main_output_dir_is_a_file_returns_output_error(tmp_path, submission_crate, mock_wb_config, monkeypatch):
    def fake_fetch(self, task_id, output_dir):
        # Mimics fetch_outputs creating the result directory before downloading
        output_dir.mkdir(parents=True, exist_ok=True)
        return {"DEMO": []}
    _mock_fetch_outputs(monkeypatch, fake_fetch)
    output_dir = tmp_path / "out"
    output_dir.write_text("not a directory")

    exit_code = _run_main(submission_crate, mock_wb_config, output_dir)

    assert exit_code == ExitCode.OUTPUT_ERROR


@pytest.mark.parametrize(
    "flag, info_shown",
    [(["-v"], True), ([], False), (["-q"], False)],
    ids=["verbose", "default", "quiet"],
)
def test_main_workbench_logs_follow_verbosity(tmp_path, capsys, submission_crate, mock_wb_config, monkeypatch, flag, info_shown):
    # Workbench loggers have their own handlers and don't propagate, so they must be
    # routed through the CLI's logging configuration. Their INFO messages are only
    # shown with -v; warnings always go to stderr.
    workbench_logger = logging.getLogger("five_safes_tes_workbench.helpers.s3")

    def fake_fetch(self, task_id, output_dir):
        workbench_logger.info("Workbench info message")
        workbench_logger.warning("Workbench warning message")
        return {}
    _mock_fetch_outputs(monkeypatch, fake_fetch)

    main([str(submission_crate), "--config_path", str(mock_wb_config), "--output_dir", str(tmp_path / "out"), *flag])

    captured = capsys.readouterr()
    assert ("Workbench info message" in captured.out) is info_shown
    assert "Workbench warning message" in captured.err
    assert "Workbench warning message" not in captured.out


@pytest.mark.parametrize("paths_dict", [{}, {"DEMO": []}], ids=["no_completed_tasks", "completed_no_files"])
def test_main_no_outputs_returns_no_results(tmp_path, submission_crate, mock_wb_config, monkeypatch, paths_dict):
    _mock_fetch_outputs(monkeypatch, lambda self, task_id, output_dir: paths_dict)

    exit_code = _run_main(submission_crate, mock_wb_config, tmp_path / "out")

    assert exit_code == ExitCode.NO_RESULTS


def test_main_write_failure_returns_output_error(tmp_path, submission_crate, mock_wb_config, monkeypatch):
    def fake_fetch(self, task_id, output_dir):
        output_dir.mkdir(parents=True, exist_ok=True)
        result = output_dir / "stdout"
        shutil.copy(RESULT_FILE, result)
        return {"DEMO": [result]}
    _mock_fetch_outputs(monkeypatch, fake_fetch)

    def raise_os_error(self, path):
        raise OSError("disk full")
    monkeypatch.setattr("fivesafe_crate_py.FiveSafesCrate.write", raise_os_error)

    exit_code = _run_main(submission_crate, mock_wb_config, tmp_path / "out")

    assert exit_code == ExitCode.OUTPUT_ERROR


def test_every_exit_code_has_a_description():
    from toolkits.config.exit_codes import EXIT_CODE_DESCRIPTIONS

    assert set(EXIT_CODE_DESCRIPTIONS) == set(ExitCode)
