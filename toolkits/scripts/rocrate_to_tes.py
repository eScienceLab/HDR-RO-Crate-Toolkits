import argparse
import json
import logging
import uuid

from pathlib import Path
from five_safes_tes_workbench.workbench import Workbench
from five_safes_tes_workbench.common.exceptions.submission_errors import SubmissionError
from fivesafe_crate_py import FiveSafesCrate
from rocrate.model.contextentity import ContextEntity
from rocrate.model.person import Person
from rocrate.utils import iso_now

from toolkits.config.logging import configure_logging
from toolkits.clients.tes_client import load_rocrate_metadata, extract_or_load_tes_message, is_tes_message_entity
from toolkits.services.validation_service import is_rocrate_metadata_valid


def parse_args(argv=None):
    """Parse command-line arguments for the RO-Crate to TES extractor."""

    parser = argparse.ArgumentParser(
        description=(
            "Extract a TES message embedded in RO-Crate metadata and submits "
            "it to the configured TES endpoint."
        ),
    )
    parser.add_argument(
        "input_path",
        help=(
            "Path to an RO-Crate metadata JSON file or to the root directory "
            "of an RO-Crate, or to a ZIP-packaged RO-Crate."
        ),
    )
    parser.add_argument(
        "--config_path",
        required=True,
        help="Path to a Five Safes TES Workbench config YAML file.",
    )
    parser.add_argument(
        "--output_dir",
        default=Path.cwd(),
        type=Path,
        help="Path to the directory to save the submission RO-Crate. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--roc_name",
        default="tes-submission-ro-crate",
        help="Name of the RO-Crate. 'tes-submission-ro-crate' by default.",
    )
    parser.add_argument(
        "--disable_roc_validator",
        action="store_true",
        help="Disable the RO-Crate validator",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Increase verbosity",
    )
    return parser.parse_args(argv)


def main(argv=None):
    """Run the CLI and print the extracted TES message as formatted JSON.

    Returns:
        int: `0` on success, `1` if the metadata file cannot be read, parsed,
        or does not contain exactly one TES payload.
    """

    args = parse_args(argv)

    logging_level = "DEBUG" if args.verbose else "INFO"
    configure_logging(logging_level)
    logger = logging.getLogger(__name__)

    try:
        crate = FiveSafesCrate(args.input_path, version="1.0")
        crate_metadata = load_rocrate_metadata(args.input_path)
        logger.info("RO-Crate metadata loaded")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        logger.error(exc)
        return 1

    if not args.disable_roc_validator:
        try:
            metadata_valid = is_rocrate_metadata_valid(crate_metadata)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            logger.error(exc)
            return 1

        if metadata_valid:
            logger.info("RO-Crate metadata validation successful")
        else:
            logger.warning("Invalid RO-Crate metadata")
            return 1

    try:
        tes_message = extract_or_load_tes_message(crate_metadata, args.input_path)
        logger.debug("TES message: \n%s", json.dumps(tes_message, indent=2))
    except ValueError as exc:
        logger.error(exc)
        return 1

    try:
        matches = [entity for entity in crate.data_entities if is_tes_message_entity(entity.properties())]
        if not matches:
            raise ValueError("No TES message found in RO-Crate metadata.")
        if len(matches) > 1:
            raise ValueError("Multiple TES message candidates found in RO-Crate metadata.")
        tes_msg_entity = matches[0]
    except ValueError as exc:
        logger.error(exc)
        return 1

    wb = Workbench()
    wb.validate(config_path=args.config_path)

    try:
        wb.build_tes.custom(**tes_message)
        task_id = wb.submit()
        logger.info(f"Submitted task ID: {task_id}")
    except SubmissionError as exc:
        logger.error(exc)
        return 1

    provider_id = "https://ror.org/027m9bs27"  # TODO: Replace with input
    provider = crate.add(ContextEntity(crate, provider_id, properties={
        "@type": "Organization",
        "name": "TRE Provider"
    }))

    agent_id = "https://orcid.org/0000-0002-1825-0097"  # TODO: Replace with input
    agent = crate.add(Person(crate, agent_id, properties={
        "name": "Person Name",
        "affiliation": provider,
    }))

    action_id = uuid.uuid4().urn
    action_properties = {
        "@type": ["AskAction", "prov:Activity"],
        "name": "Submit TES task",
        "agent": agent,
        "provider": provider,
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
    }
    crate_tes_task = crate.add(ContextEntity(crate, identifier=crate_tes_task_id, properties=crate_tes_task_properties))
    crate.root_dataset.append_to("identifier", crate_tes_task)

    crate.root_dataset["dateModified"] = iso_now()

    roc_output_dir = args.output_dir / args.roc_name
    crate.write(roc_output_dir)
    logger.info(f"RO-Crate {args.roc_name} created at {args.output_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
