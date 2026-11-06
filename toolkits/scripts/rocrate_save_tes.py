import argparse
import json
import logging

import yaml
from botocore.exceptions import BotoCoreError, ClientError
from pathlib import Path
from five_safes_tes_workbench.common.exceptions.base import WorkbenchError
from five_safes_tes_workbench.workbench import Workbench
from fivesafe_crate_py import FiveSafesCrate

from toolkits.config.exit_codes import ExitCode, exit_codes_epilog
from toolkits.config.logging import configure_logging
from toolkits.services.rocrate_service import create_tes_result_crate, get_tes_task_id

def parse_args(argv=None):
    """Parse command-line arguments for the CLI tool."""

    parser = argparse.ArgumentParser(
        description="Save TES result in an RO-Crate.",
        epilog=exit_codes_epilog(
            ExitCode.SUCCESS, ExitCode.GENERAL_ERROR, ExitCode.USAGE_ERROR, ExitCode.INPUT_ERROR,
            ExitCode.SERVICE_ERROR, ExitCode.OUTPUT_ERROR, ExitCode.NO_RESULTS,
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
        "--output_dir",
        default=Path.cwd(),
        type=Path,
        help="Path to the directory to save the result RO-Crate. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--roc_name",
        default="tes-result-ro-crate",
        help="Name of the RO-Crate. 'tes-result-ro-crate' by default.",
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
    """Run the CLI and save the TES result in an RO-Crate.

    Returns:
        ExitCode: `SUCCESS` on success, otherwise `INPUT_ERROR`, `SERVICE_ERROR`,
        `NO_RESULTS` or `OUTPUT_ERROR` depending on which step failed.
    """

    args = parse_args(argv)

    logging_level = "DEBUG" if args.verbose else "WARNING" if args.quiet else "INFO"
    configure_logging(logging_level)
    logger = logging.getLogger(__name__)

    try:
        crate = FiveSafesCrate(args.input_path, version="1.0")
        logger.info("RO-Crate loaded")
        task_id = get_tes_task_id(crate)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        logger.error(exc)
        return ExitCode.INPUT_ERROR

    wb = Workbench()
    try:
        # Raises FileNotFoundError, yaml.YAMLError or pydantic.ValidationError (a ValueError)
        wb.validate(config_path=args.config_path)
    except (OSError, yaml.YAMLError, ValueError) as exc:
        logger.error(f"Invalid Workbench config {args.config_path}: {exc}")
        return ExitCode.INPUT_ERROR

    # Save outputs at roc_output_dir
    roc_output_dir = args.output_dir / args.roc_name
    try:
        # fetch_outputs raises untyped errors from its auth/STS/S3 helpers,
        # not WorkbenchError subclasses; OSError covers requests' HTTP errors.
        paths_dict = wb.fetch_outputs(task_id=task_id, output_dir=roc_output_dir)
    except (WorkbenchError, ValueError, RuntimeError, OSError, ClientError, BotoCoreError) as exc:
        logger.error(f"Could not fetch outputs for TES task {task_id}: {exc}")
        return ExitCode.SERVICE_ERROR

    # fetch_outputs returns {} when no task has completed, and {tre: []} when a
    # completed task produced no files
    if not any(paths_dict.values()):
        # TODO: Handle "in progress" tasks when function becomes available in workbench
        logger.error("TES task has no outputs; result RO-Crate was not created.")
        return ExitCode.NO_RESULTS

    try:
        crate = create_tes_result_crate(crate, paths_dict, roc_output_dir)
        crate.write(roc_output_dir)
    except (OSError, ValueError) as exc:
        logger.error(f"RO-Crate {args.roc_name} could not be saved to {args.output_dir}: {exc}")
        return ExitCode.OUTPUT_ERROR

    logger.info(f"RO-Crate {args.roc_name} created at {args.output_dir}")
    return ExitCode.SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())
