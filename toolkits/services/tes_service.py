from fivesafe_crate_py import FiveSafesCrate
from rocrate.model import File, ContextEntity

from toolkits.clients.tes_client import is_tes_message_entity


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
