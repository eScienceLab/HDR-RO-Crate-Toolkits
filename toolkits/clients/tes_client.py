import json
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from toolkits.config.settings import ROCRATE_METADATA_FILENAME


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


def extract_tes_message(crate_metadata):
    """Extract the unique TES message embedded in RO-Crate metadata.

    The function scans the RO-Crate `@graph` for `CreativeWork` entities whose
    `text` property contains stringified JSON. Parsed payloads are treated as
    TES candidates only if they satisfy `is_tes_payload`.

    Raises:
        ValueError: if `@graph` is missing or invalid, if no TES payload is
            found, or if more than one TES candidate is present.
    """

    graph = crate_metadata.get("@graph")
    if not isinstance(graph, list):
        raise ValueError("RO-Crate metadata must contain an '@graph' array.")

    matches = []

    for entity in graph:
        if not isinstance(entity, dict):
            continue
        if entity.get("@type") != "CreativeWork":
            continue

        text = entity.get("text")
        if not isinstance(text, str):
            continue

        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue

        if is_tes_payload(payload):
            matches.append(payload)

    if not matches:
        raise ValueError("No TES message found in RO-Crate metadata.")
    if len(matches) > 1:
        raise ValueError("Multiple TES message candidates found in RO-Crate metadata.")

    return matches[0]


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
