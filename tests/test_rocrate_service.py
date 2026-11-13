from pathlib import Path

import pytest
from fivesafe_crate_py import FiveSafesCrate

from toolkits.services.rocrate_service import (
    create_tes_submission_crate,
    get_tes_task_id,
)

DATA_DIR = Path(__file__).parent / "data"


@pytest.mark.parametrize(
    "crate_dir",
    ["5s-tes-pre-submission", "fortress-5s-tes-pre-submission"],
)
def test_get_tes_task_id_round_trips_submission_crate(tmp_path, crate_dir):
    """A crate written by create_tes_submission_crate can be read back."""
    crate = FiveSafesCrate(DATA_DIR / crate_dir)
    crate = create_tes_submission_crate(crate, "42")
    crate.write(tmp_path)

    assert get_tes_task_id(FiveSafesCrate(tmp_path)) == 42
