import json
import requests

from pathlib import Path
from zipfile import BadZipFile, ZipFile
from urllib.parse import urljoin

from toolkits.config.settings import (
    TASK_SERVICE_API_URL,
    TASK_SUBMISSION_API_TOKEN,
    ROCRATE_METADATA_FILENAME,
    TES_TASK_SCHEMA_ID,
)


def create_tes_task(tes_message: dict) -> dict:
    """Create a task by sending the TES message to the 5S-TES submission API.
    
    This function sends a TES message to the 5S-TES submission API endpoint 
    via HTTP POST request. Successful responses are expected to contain a 
    JSON body, which is returned as a dictionary.

    Args:
        tes_message (dict)

    Returns:
        The parsed JSON response from the API.

    Raises:
        TypeError: If `tes_message` is not a dictionary.
        requests.exceptions.RequestException: If the request failed.
        ValueError: If the response body cannot be decoded as JSON.
    """

    if not isinstance(tes_message, dict):
        raise TypeError("tes_message must be a dictionary")

    url = urljoin(TASK_SERVICE_API_URL, "v1/tasks")
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json-patch+json",
        "Authorization": "Bearer " + TASK_SUBMISSION_API_TOKEN
    }
    response = requests.post(url, headers=headers, data=json.dumps(tes_message))
    response.raise_for_status()
    return response.json()

def is_valid_executor(executor):
    """Return True when `executor` matches the minimal TES executor shape.

    A valid executor must be a JSON object with:
    - `image`: a string naming the container image
    - `command`: an array of strings representing the command to run and its arguments
    """

    return (
        isinstance(executor, dict)
        and isinstance(executor.get("image"), str)
        and isinstance(executor.get("command"), list)
        and all(isinstance(part, str) for part in executor["command"])
    )


def is_tes_payload(payload):
    """Return True when `payload` looks like a TES task description.

    The current discriminator is the required `executors` field. It must be
    an array of objects, and every executor must satisfy the minimal TES
    executor structure checked by `is_valid_executor`.
    """

    if not isinstance(payload, dict):
        return False

    executors = payload.get("executors")
    if not isinstance(executors, list):
        return False

    return bool(executors) and all(
        is_valid_executor(executor) for executor in executors
    )


def conforms_to_tes_task_schema(entity):
    """Return True when an RO-Crate entity declares the TES task schema."""

    conforms_to = entity.get("conformsTo")
    if isinstance(conforms_to, str):
        return conforms_to == TES_TASK_SCHEMA_ID
    if isinstance(conforms_to, dict):
        return conforms_to.get("@id") == TES_TASK_SCHEMA_ID
    if isinstance(conforms_to, list):
        return any(
            (
                isinstance(item, str) and item == TES_TASK_SCHEMA_ID
            )
            or (
                isinstance(item, dict) and item.get("@id") == TES_TASK_SCHEMA_ID
            )
            for item in conforms_to
        )
    return False


def is_creative_work(entity):
    """Return True when the entity type includes `CreativeWork`."""

    entity_type = entity.get("@type")
    if isinstance(entity_type, str):
        return entity_type == "CreativeWork"
    if isinstance(entity_type, list):
        return "CreativeWork" in entity_type
    return False


def is_tes_message_entity(entity):
    """Return True when the entity matches the TES message metadata shape."""

    return (
        isinstance(entity, dict)
        and is_creative_work(entity)
        and conforms_to_tes_task_schema(entity)
        and entity.get("encodingFormat") == "application/json"
        and isinstance(entity.get("text"), str)
    )


def extract_tes_message(crate_metadata):
    """Extract the unique TES message embedded in RO-Crate metadata.

    The function scans the RO-Crate `@graph` for a single `CreativeWork`
    entity whose `conformsTo` property points to the TES task schema, whose
    `encodingFormat` is `application/json`, and whose `text` property is a
    string containing a TES task payload.

    Raises:
        ValueError: if `@graph` is missing or invalid, if no TES metadata
            candidate is found, if more than one candidate is present, or if
            the TES content is not valid.
    """

    graph = crate_metadata.get("@graph")
    if not isinstance(graph, list):
        raise ValueError("RO-Crate metadata must contain an '@graph' array.")

    matches = [entity for entity in graph if is_tes_message_entity(entity)]

    if not matches:
        raise ValueError("No TES message found in RO-Crate metadata.")
    if len(matches) > 1:
        raise ValueError("Multiple TES message candidates found in RO-Crate metadata.")

    try:
        payload = json.loads(matches[0]["text"])
    except json.JSONDecodeError as exc:
        raise ValueError("TES message content is not valid JSON.") from exc

    if not is_tes_payload(payload):
        raise ValueError("TES message content is not a valid TES payload.")

    return payload


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
