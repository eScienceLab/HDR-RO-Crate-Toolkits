import uuid

from pathlib import Path
from fivesafe_crate_py import FiveSafesCrate
from rocrate.model import File, ContextEntity, Person
from rocrate.utils import iso_now

from toolkits.clients.tes_client import is_tes_message_entity
from toolkits.config.settings import ROCRATE_METADATA_FILENAME, TES_TASK_ID_SCHEMA_ID


def is_valid_crate_path(input_path: Path, output_path: Path) -> bool:
    """Returns True if output crate will not be nested within the input crate.

    The input path could be a path to an RO-Crate directory, a metadata file or a zip file.
    """

    if input_path.is_file() and input_path.suffix.lower() == ".zip":
        return True

    if input_path.is_dir():
        input_dir = input_path
    elif input_path.is_file() and input_path.name == ROCRATE_METADATA_FILENAME:
        input_dir = input_path.parent
    else:
        return False

    return not "".join(input_dir.resolve().parts) in "".join(output_path.resolve().parts)

def get_tes_task_id(crate: FiveSafesCrate) -> int:
    """Returns the TES task ID in the RO-Crate.

    Args:
        crate: The RO-Crate to extract TES message from.

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
        and task_id_entity == entity["identifier"]
    ]
    if not action_matches:
        raise ValueError("The TES task submission action entity must carry the TES task ID.")

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
    agent_id = "https://orcid.org/0000-0002-1825-0097"
    agent = crate.add(Person(crate, agent_id, properties={
        "name": "Person Name",
        "affiliation": provider,
    }))
    return crate, agent, provider

def create_tes_submission_crate(crate: FiveSafesCrate, task_id: str) -> FiveSafesCrate:
    """Returns a 5S TES submission crate.
    
    Args:
        crate: The RO-Crate to add submission information to.
        task_id: The ID of the successfully submitted task.
    
    Returns:
        A Five Safes RO-Crate
    """

    crate, agent, provider = add_placeholder_org_and_author(crate)

    tes_msg_entity = get_tes_msg_entity(crate)

    action_id = uuid.uuid4().urn
    action_properties = {
        "@type": ["AskAction", "prov:Activity"],
        "name": "TES task submission",
        "agent": agent,
        "provider": provider,
        "recipient": provider,
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
    action.append_to("identifier", crate_tes_task)
    
    crate.root_dataset["dateModified"] = iso_now()

    return crate

def create_tes_result_crate(crate: FiveSafesCrate, paths_dict: dict, roc_output_dir) -> FiveSafesCrate:
    """Returns a 5S TES result crate.

    Args:
        crate: The RO-Crate to add result information to.

    Returns:
        A Five Safes RO-Crate
    """

    result_entities = []
    paths = [path for path_list in paths_dict.values() for path in path_list]
    for path in paths:
        relative_path = path.relative_to(roc_output_dir)
        result_entity = crate.add_file(path.as_posix(), relative_path.as_posix())
        result_entities.append(result_entity)

    crate, agent, provider = add_placeholder_org_and_author(crate)

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

    crate.root_dataset["dateModified"] = iso_now()

    return crate