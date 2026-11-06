import argparse
import json
import logging

import yaml
from pathlib import Path
from five_safes_tes_workbench.workbench import Workbench
from five_safes_tes_workbench.common.exceptions.base import WorkbenchError
from fivesafe_crate_py import FiveSafesCrate

from toolkits.config.exit_codes import ExitCode, exit_codes_epilog
from toolkits.config.logging import configure_logging
from toolkits.clients.tes_client import load_rocrate_metadata, extract_or_load_tes_message
from toolkits.services.validation_service import is_rocrate_metadata_valid
from toolkits.services.rocrate_service import is_valid_output_rocrate_path, create_tes_submission_crate


def parse_args(argv=None):
    """Parse command-line arguments for the RO-Crate to TES extractor."""

    parser = argparse.ArgumentParser(
        description=(
            "Extract a TES message embedded in RO-Crate metadata and submits "
            "it to the configured TES endpoint."
        ),
        epilog=exit_codes_epilog(
            ExitCode.SUCCESS, ExitCode.GENERAL_ERROR, ExitCode.USAGE_ERROR, ExitCode.INPUT_ERROR,
            ExitCode.VALIDATION_FAILED, ExitCode.SERVICE_ERROR, ExitCode.OUTPUT_ERROR,
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
        "--output_rocrate",
        default=Path.cwd() / "tes-submission-ro-crate",
        type=Path,
        help=(
            "Path to the submission RO-Crate. "
            "Defaults to 'tes-submission-ro-crate' in the current working directory."
        ),
    )
    parser.add_argument(
        "--disable_roc_validator",
        action="store_true",
        help="Disable the RO-Crate validator",
    )
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Increase verbosity",
    )
    verbosity.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Only show warnings and errors",
    )
    return parser.parse_args(argv)


def main(argv=None):
    """Submit the TES message embedded in an RO-Crate and write a submission RO-Crate.

    Returns:
        ExitCode: `SUCCESS` on success, otherwise `INPUT_ERROR`, `VALIDATION_FAILED`,
        `SERVICE_ERROR` or `OUTPUT_ERROR` depending on which step failed.
    """

    args = parse_args(argv)

    logging_level = "DEBUG" if args.verbose else "WARNING" if args.quiet else "INFO"
    configure_logging(logging_level)
    logger = logging.getLogger(__name__)

    try:
        crate = FiveSafesCrate(args.input_path, version="1.0")
        crate_metadata = load_rocrate_metadata(args.input_path)
        logger.info("RO-Crate metadata loaded")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        logger.error(exc)
        return ExitCode.INPUT_ERROR

    if not is_valid_output_rocrate_path(Path(args.input_path), args.output_rocrate):
        logger.error("The output path cannot be nested in the input path")
        return ExitCode.OUTPUT_ERROR

    if not args.disable_roc_validator:
        try:
            metadata_valid = is_rocrate_metadata_valid(crate_metadata)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            # OSError covers requests' connection/HTTP errors from the validator API
            logger.error(exc)
            return ExitCode.SERVICE_ERROR

        if not metadata_valid:
            logger.error("Invalid RO-Crate metadata")
            return ExitCode.VALIDATION_FAILED
        logger.info("RO-Crate metadata validation successful")

    try:
        tes_message = extract_or_load_tes_message(crate_metadata, args.input_path)
        logger.debug("TES message: \n%s", json.dumps(tes_message, indent=2))
    except (OSError, ValueError) as exc:
        # OSError: a TES file referenced from ro-crate-metadata.json is missing or unreadable
        logger.error(exc)
        return ExitCode.INPUT_ERROR

    wb = Workbench()
    try:
        # Raises FileNotFoundError, yaml.YAMLError, pydantic.ValidationError (a ValueError)
        # or a WorkbenchError subclass
        wb.validate(config_path=args.config_path)
    except (OSError, yaml.YAMLError, ValueError, WorkbenchError) as exc:
        # WorkbenchError: ConfigValidationError/AuthValidationError for missing or empty values
        logger.error(f"Invalid Workbench config {args.config_path}: {exc}")
        return ExitCode.INPUT_ERROR

    try:
        wb.build_tes.custom(**tes_message)
        task_id = wb.submit()
        logger.info(f"Submitted task ID: {task_id}")
    except WorkbenchError as exc:
        logger.error(exc)
        return ExitCode.SERVICE_ERROR

    try:
        crate = create_tes_submission_crate(crate, task_id)
        crate.write(args.output_rocrate)
    except (OSError, ValueError) as exc:
        logger.error(
            f"TES task {task_id} was submitted, but RO-Crate {args.output_rocrate.name} "
            f"could not be saved to {args.output_rocrate.parent}: {exc}"
        )
        return ExitCode.OUTPUT_ERROR

    logger.info(f"RO-Crate {args.output_rocrate.name} created at {args.output_rocrate.parent}")
    return ExitCode.SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())
