import uuid

from fivesafe_crate_py import FiveSafesCrate
from rocrate.model import ContextEntity

from toolkits.services.tes_service import get_tes_msg_entity


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

    tes_msg_entity = get_tes_msg_entity(crate)

    action_id = uuid.uuid4().urn
    action_properties = {
        "@type": ["CreateAction", "prov:Activity"],
        # TODO: "agent" - Person or Organisation
        "actionStatus": {"@id": "http://schema.org/CompletedActionStatus"},
        "object": tes_msg_entity,
    }
    if result_entities:
        action_properties["result"] = result_entity if len(result_entities) == 1 else result_entities
    action = crate.add(ContextEntity(crate, identifier=action_id, properties=action_properties))
    crate.root_dataset["mentions"] = [action]

    return crate