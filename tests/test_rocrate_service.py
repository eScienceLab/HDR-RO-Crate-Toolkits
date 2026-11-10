import json
import shutil
from pathlib import Path

import pytest
from fivesafe_crate_py import FiveSafesCrate

from toolkits.services.rocrate_service import get_tes_task_id


SUBMISSION_CRATE_DIR = Path(__file__).parent / "data" / "5s-tes-submission"
TASK_ID_REF = {"@id": "urn:uuid:1ec84024-798f-47b0-84bc-26a4a603a1ec"}
OTHER_REF = {"@id": "#other-identifier"}


def _submission_crate(tmp_path, identifier):
    """Copy the submission crate fixture, replacing the submission action's identifier."""

    crate_dir = tmp_path / "submission-crate"
    shutil.copytree(SUBMISSION_CRATE_DIR, crate_dir)
    metadata_path = crate_dir / "ro-crate-metadata.json"
    metadata = json.loads(metadata_path.read_text())
    for entity in metadata["@graph"]:
        if "AskAction" in entity.get("@type", []):
            if identifier is None:
                entity.pop("identifier", None)
            else:
                entity["identifier"] = identifier
    metadata_path.write_text(json.dumps(metadata))
    return FiveSafesCrate(str(crate_dir), version="1.0")


@pytest.mark.parametrize(
    "identifier",
    [
        TASK_ID_REF,
        [TASK_ID_REF],
        [OTHER_REF, TASK_ID_REF],
        ["plain-string-identifier", TASK_ID_REF],
    ],
    ids=["single", "list", "list-with-other-entity", "list-with-string"],
)
def test_get_tes_task_id_accepts_single_or_list_identifier(tmp_path, identifier):
    crate = _submission_crate(tmp_path, identifier)

    assert get_tes_task_id(crate) == 1


@pytest.mark.parametrize(
    "identifier",
    [None, OTHER_REF, [OTHER_REF], []],
    ids=["missing", "other-entity", "list-without-task-id", "empty-list"],
)
def test_get_tes_task_id_rejects_action_without_task_id(tmp_path, identifier):
    crate = _submission_crate(tmp_path, identifier)

    with pytest.raises(ValueError, match="must carry the TES task ID"):
        get_tes_task_id(crate)
