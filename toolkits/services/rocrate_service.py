import json
import logging
import shutil
import tempfile
import uuid

from pathlib import Path
from zipfile import BadZipFile, ZipFile, is_zipfile
from fivesafe_crate_py import FiveSafesCrate
from rocrate.model import File, ContextEntity, Person
from rocrate.utils import iso_now

from toolkits.services.tes_service import is_tes_message_entity
from toolkits.config.settings import ROCRATE_METADATA_FILENAME, TES_TASK_ID_SCHEMA_ID


logger = logging.getLogger(__name__)


def is_valid_output_rocrate_path(input_path: Path, output_path: Path) -> bool:
    """Returns True if output crate will not be nested within the input crate."""

    if input_path.is_file() and input_path.name == ROCRATE_METADATA_FILENAME:
        input_dir = input_path.parent
    else:
        input_dir = input_path

    return not "".join(input_dir.resolve().parts) in "".join(output_path.resolve().parts)

def _as_list(value) -> list:
    """Return a property value as a list, since JSON-LD allows a single value or a list."""
    return value if isinstance(value, list) else [value]


def get_tes_task_id_entity(crate: FiveSafesCrate) -> ContextEntity | None:
    """Returns the TES task ID entity in the RO-Crate.

    Args:
        crate: The RO-Crate to extract TES task ID entity from.

    Raises:
        ValueError: If no TES task ID entity is found, or if more than one entity is present.
    """

    entities = crate.data_entities + crate.contextual_entities
    matches = [
        entity for entity in entities 
        if entity.type == "PropertyValue" and entity.get("propertyID") == TES_TASK_ID_SCHEMA_ID
    ]
    if not matches:
        raise ValueError("No TES task ID found in RO-Crate metadata.")
    if len(matches) > 1:
        raise ValueError("Multiple TES task IDs found in RO-Crate metadata.")
    task_id_entity = matches[0]

    action_matches = [
        entity for entity in entities
        if isinstance(entity.type, list) 
        and "AskAction" in entity.type and "prov:Activity" in entity.type
        and task_id_entity in _as_list(entity.get("identifier"))
    ]
    if not action_matches:
        raise ValueError("The TES task submission action entity must carry the TES task ID.")

    return task_id_entity


def get_tes_task_id(crate: FiveSafesCrate) -> int:
    """Returns the TES task ID in the RO-Crate."""

    task_id_entity = get_tes_task_id_entity(crate)
    return int(task_id_entity["value"])


def get_tes_msg_entity(crate: FiveSafesCrate) -> File | ContextEntity:
    """Return the unique TES message in the RO-Crate.

    Args:
        crate: The RO-Crate to extract TES message from.

    Returns:
        The TES message entity, which could be a File instance or a ContextEntity instance.
    
    Raises:
        ValueError: If no TES message entity is found, or if more than one entity is present.
    """

    entities = crate.data_entities + crate.contextual_entities
    matches = [entity for entity in entities if is_tes_message_entity(entity.properties())]
    if not matches:
        raise ValueError("No TES message found in RO-Crate metadata.")
    if len(matches) > 1:
        raise ValueError("Multiple TES message candidates found in RO-Crate metadata.")

    return matches[0]


def add_placeholder_org_and_author(crate):
    # TODO: Remove placeholder
    provider_id = "https://ror.org/027m9bs27"
    provider = crate.add(ContextEntity(crate, provider_id, properties={
        "@type": "Organization",
        "name": "TRE Provider"
    }))
    recipient_id = "https://ror.org/05gq02987"
    recipient = crate.add(ContextEntity(crate, recipient_id, properties={
        "@type": "Organization",
        "name": "Brown University"
    }))
    agent_id = "https://orcid.org/0000-0002-1825-0097"
    agent = crate.add(Person(crate, agent_id, properties={
        "name": "Josiah Stinkney Carberry",
        "affiliation": recipient,
    }))
    return crate, agent, recipient, provider


def initialise_snapshot(input_crate: FiveSafesCrate, version: int | None = None) -> FiveSafesCrate:
    """Returns a Five Safes RO-Crate with the required entities and 
    Root Data Entity (RDE) properties extracted from the input crate.

    Args:
        input_crate: The pre-submission or submission RO-Crate.

    Returns:
        An initialised snapshot Five Safes RO-Crate
    """

    # Get new identifier
    if version is None:
        previous_version = input_crate.root_dataset.get("version")
        if previous_version is None:
            raise ValueError("The version number of the snapshot RO-Crate should be provided if the input RO-Crate is not a snapshot.")
        version = int(previous_version) + 1
    id = f"{input_crate.root_dataset.get("dct:isVersionOf")}/versions/{version}/"

    # Initialise crate
    crate = FiveSafesCrate(version="1.0-DRAFT", rocrate_base_version="1.3", root_dataset_id=id, identifier=id)

    # Update RDE
    crate.root_dataset["dateCreated"] = iso_now()
    for key, value in input_crate.root_dataset.properties().items():
        if key not in crate.root_dataset.properties():
            crate.root_dataset[key] = value
    crate.root_dataset["pav:previousVersion"] = input_crate.root_dataset
    crate.root_dataset["version"] = version

    # Other entities
    for entity in input_crate.get_entities():
        if entity == input_crate.root_dataset:
            continue
        if crate.dereference(entity.id) is None:
            crate.add_jsonld(entity.properties())

    return crate


def create_tes_submission_crate(input_crate: FiveSafesCrate, task_id: str) -> FiveSafesCrate:
    """Returns a 5S TES submission crate (snapshot).

    Args:
        input_crate: The pre-submission RO-Crate with tes message.
        task_id: The ID of the successfully submitted task.

    Returns:
        A Five Safes RO-Crate with submission information
    """

    crate = initialise_snapshot(input_crate)

    # Add task submission entities

    crate, agent, recipient, provider = add_placeholder_org_and_author(crate)

    tes_msg_entity = get_tes_msg_entity(input_crate)

    action_id = uuid.uuid4().urn
    action_properties = {
        "@type": ["AskAction", "prov:Activity"],
        "name": "TES task submission",
        "agent": agent,
        "provider": provider,
        "recipient": recipient,
        "endTime": iso_now(),
        "actionStatus": {"@id": "http://schema.org/CompletedActionStatus"},
        "object": tes_msg_entity,
    }
    action = crate.add(ContextEntity(crate, identifier=action_id, properties=action_properties))
    crate.root_dataset.append_to("mentions", action)
    
    crate_tes_task_id = uuid.uuid4().urn
    crate_tes_task_properties = {
        "@type": "PropertyValue",
        "name": "TES Task ID",
        "value": task_id,
        "propertyID": TES_TASK_ID_SCHEMA_ID,
        "url": "https://example.org/tes/v1/tasks/1",  # TODO: Placeholder
    }
    crate_tes_task = crate.add(ContextEntity(crate, identifier=crate_tes_task_id, properties=crate_tes_task_properties))
    action.append_to("identifier", crate_tes_task, compact=True)

    # Note that this should only be done before first crate.write(), 
    # i.e. snapshots or first write of working record
    crate.root_dataset["datePublished"] = iso_now()

    return crate


def create_tes_result_crate(input_crate: FiveSafesCrate, paths_dict: dict, roc_output_dir) -> FiveSafesCrate:
    """Returns a 5S TES result crate (snapshot).

    Args:
        input_crate: The submission RO-Crate with a TES task ID.

    Returns:
        A Five Safes RO-Crate with results of a TES task
    """

    crate = initialise_snapshot(input_crate)

    result_entities = []
    paths = [path for path_list in paths_dict.values() for path in path_list]
    for path in paths:
        relative_path = path.relative_to(roc_output_dir)
        result_entity = crate.add_file(path.as_posix(), relative_path.as_posix())
        result_entities.append(result_entity)

    crate, agent, _, provider = add_placeholder_org_and_author(crate)

    tes_msg_entity = get_tes_msg_entity(crate)

    action_id = uuid.uuid4().urn
    action_properties = {
        "@type": ["CreateAction", "prov:Activity"],
        "name": "TES task result",
        "agent": agent,
        "provider": provider,
        "endTime": iso_now(),  # TODO: Get end time from workbench/API if possible
        "actionStatus": {"@id": "http://schema.org/CompletedActionStatus"},
        "object": tes_msg_entity,
    }
    if result_entities:
        action_properties["result"] = result_entity if len(result_entities) == 1 else result_entities
    action = crate.add(ContextEntity(crate, identifier=action_id, properties=action_properties))
    crate.root_dataset.append_to("mentions", action)

    crate_tes_task = get_tes_task_id_entity(crate)
    action.append_to("identifier", crate_tes_task, compact=True)

    # Note that this should only be done before first crate.write(), 
    # i.e. snapshots or first write of working record
    crate.root_dataset["datePublished"] = iso_now()

    return crate


def write_crate(crate: FiveSafesCrate, input_path: Path, output_rocrate: Path) -> bool:
    """Copy RO-Crate payload files from a directory or ZIP archive, and write metadata."""

    try:
        temp_dir = Path(tempfile.mkdtemp(dir=output_rocrate.parent, prefix=f".{output_rocrate.name}_tmp_"))
        backup_dir = Path(tempfile.mkdtemp(dir=output_rocrate.parent, prefix=f".{output_rocrate.name}_bak_"))

        if input_path.is_dir():
            shutil.copytree(input_path, temp_dir, dirs_exist_ok=True)
        elif is_zipfile(input_path):
            with ZipFile(input_path, "r") as zip_file:
                zip_file.extractall(temp_dir)
        else:
            shutil.copytree(input_path.parent, temp_dir, dirs_exist_ok=True)
        crate.write(str(temp_dir))

        if output_rocrate.exists():
            output_rocrate.rename(backup_dir)

        temp_dir.rename(output_rocrate)
        temp_dir = None

        if backup_dir:
            try:
                shutil.rmtree(backup_dir)
                backup_dir = None
            except OSError as exc:
                logger.warning(
                    f"RO-Crate backup could not be removed at {backup_dir}: {exc}"
                )

        return True
    except (OSError, shutil.Error, ValueError, BadZipFile):
        if backup_dir:
            if output_rocrate.exists():
                shutil.rmtree(output_rocrate)
            backup_dir.rename(output_rocrate)
            backup_dir = None
        raise


def resolve_metadata_path(input_path):
    """Resolve an input path to the RO-Crate metadata JSON file.

    The input may be either a direct path to `ro-crate-metadata.json` or the
    root directory of an RO-Crate containing that file.

    Raises:
        ValueError: if the input path does not exist or does not resolve to an
            RO-Crate metadata JSON file.
    """

    path = Path(input_path)
    if not path.exists():
        raise ValueError(f"Input path does not exist: {path}")

    if path.is_dir():
        metadata_path = path / ROCRATE_METADATA_FILENAME
        if not metadata_path.is_file():
            raise ValueError(f"RO-Crate metadata file not found at: {metadata_path}")
        return metadata_path

    if path.is_file():
        return path

    raise ValueError(f"Input path is not a file or directory: {path}")


def load_rocrate_metadata(input_path):
    """Load RO-Crate metadata JSON from a file, crate directory, or ZIP archive."""

    path = Path(input_path)
    if path.is_file() and path.suffix.lower() == ".zip":
        try:
            with ZipFile(path) as zip_file:
                with zip_file.open(ROCRATE_METADATA_FILENAME) as handle:
                    return json.load(handle)
        except KeyError as exc:
            raise ValueError(
                f"RO-Crate metadata file not found in archive: {path}"
            ) from exc
        except BadZipFile as exc:
            raise ValueError(f"Invalid ZIP archive: {path}") from exc

    metadata_path = resolve_metadata_path(path)
    with metadata_path.open(encoding="utf-8") as handle:
        return json.load(handle)
