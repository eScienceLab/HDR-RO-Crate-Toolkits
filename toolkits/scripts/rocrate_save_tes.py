import argparse
import json
import logging

from pathlib import Path
# from five_safes_tes_workbench.workbench import Workbench
from fivesafe_crate_py import FiveSafesCrate

from toolkits.config.logging import configure_logging
from toolkits.services.rocrate_service import create_tes_result_crate

def parse_args(argv=None):
    """Parse command-line arguments for the CLI tool."""

    parser = argparse.ArgumentParser(
        description="Save TES result in an RO-Crate.",
    )
    # TODO: Read task_id from an RO-Crate metadata file and remove this arg
    parser.add_argument(
        "task_id",
        type=int,
        help="Task ID of the submitted TES task."
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
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Increase verbosity",
    )
    # TODO: Remove the following two arguments with temp fix
    parser.add_argument("--s3_endpoint", default="http://localhost:9000")
    parser.add_argument("--s3_output_bucket", required=True)
    return parser.parse_args(argv)


def main(argv=None):
    """Run the CLI and save the TES result in an RO-Crate.

    Returns:
        int: `0` on success.
    """

    args = parse_args(argv)
    
    logging_level = "DEBUG" if args.verbose else "INFO"
    configure_logging(logging_level)
    logger = logging.getLogger(__name__)

    # Temporary Fix ===============================
    # The endpoint used in get_project_s3_info is currently 404 not found
    # TODO: Remove temporary fix when get_project_s3_info is working,
    #       which would be when 5S TES deployment version is bumped to 3.2.3

    import five_safes_tes_workbench.helpers.project_s3_info
    from five_safes_tes_workbench.schema.config_schema import ConfigValidationModel
    from five_safes_tes_workbench.helpers.project_s3_info import ProjectS3Info

    def patched_get_project_s3_info(project_name: str, config: ConfigValidationModel) -> ProjectS3Info:
        return ProjectS3Info(output_bucket=args.s3_output_bucket, api_endpoint=args.s3_endpoint)
    five_safes_tes_workbench.helpers.project_s3_info.get_project_s3_info = patched_get_project_s3_info

    # TODO: Move the following line to the top
    from five_safes_tes_workbench.workbench import Workbench
    # End Temporary Fix ===========================

    try:
        crate = FiveSafesCrate(args.input_path, version="1.0")
        logger.info("RO-Crate loaded")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        logger.error(exc)
        return 1

    wb = Workbench()
    wb.validate(config_path=args.config_path)

    roc_output_dir = args.output_dir / args.roc_name
    paths_dict = wb.fetch_outputs(task_id=args.task_id, output_dir=roc_output_dir)

    if paths_dict:
        try:
            crate = create_tes_result_crate(crate, paths_dict, roc_output_dir)
        except ValueError as exc:
            logger.error(exc)
            return 1
        crate.write(roc_output_dir)
    else:
        # TODO: In progress or does not exist
        pass

    logger.info(f"RO-Crate {args.roc_name} created at {args.output_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
