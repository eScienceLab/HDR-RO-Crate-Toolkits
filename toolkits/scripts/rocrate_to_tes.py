import argparse
import json
import logging

from five_safes_tes_workbench.workbench import Workbench
from five_safes_tes_workbench.common.exceptions.submission_errors import SubmissionError

from toolkits.config.logging import configure_logging
from toolkits.clients.tes_client import load_rocrate_metadata, extract_or_load_tes_message
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

    wb = Workbench()
    wb.validate(config_path=args.config_path)

    try:
        wb.build_tes.custom(**tes_message)
        task_id = wb.submit()
        logger.info(f"Submitted task ID: {task_id}")
    except SubmissionError as exc:
        logger.error(exc)
        return 1


    return 0


if __name__ == "__main__":
    raise SystemExit(main())
