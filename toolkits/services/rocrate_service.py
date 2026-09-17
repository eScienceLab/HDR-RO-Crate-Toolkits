import uuid

from fivesafe_crate_py import FiveSafesCrate
from rocrate.model import File, ContextEntity, Person
from rocrate.utils import iso_now

from toolkits.clients.tes_client import is_tes_message_entity


def get_tes_task_id(crate: FiveSafesCrate) -> int:
    """Returns the TES task ID in the RO-Crate.

    Args:
        crate: The RO-Crate to extract TES message from.

    Raises:
        ValueError: If no TES task ID entity is found, or if more than one entity is present.
    """

    # TODO: Use propertyID (?) to find TES task ID

    entities = crate.data_entities + crate.contextual_entities
    matches = [entity for entity in entities if entity.type == "PropertyValue"] 
    if not matches:
        raise ValueError("No TES task ID found in RO-Crate metadata.")
    if len(matches) > 1:
        raise ValueError("Multiple TES task IDs found in RO-Crate metadata.")

    task_id_entity = matches[0]
    if task_id_entity not in crate.root_dataset["identifier"]:
        raise ValueError("The Root Data Entity of the RO-Crate metadaty must carry the TES task ID.")

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