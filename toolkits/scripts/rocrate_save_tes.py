import argparse
import logging

from pathlib import Path
# from five_safes_tes_workbench.workbench import Workbench

from toolkits.clients.tes_client import load_rocrate_metadata


logging.disable(logging.INFO)


def parse_args(argv=None):
    """Parse command-line arguments for the CLI tool."""

    parser = argparse.ArgumentParser(
        description="Save TES result in an RO-Crate.",
    )
    parser.add_argument(
        "task_id",
        type=int,
        help="Task ID of the submitted TES task."
    )
    # TODO: Uncomment and replace task_id arg 
    # parser.add_argument(
    #     "input_path",
    #     help=(
    #         "Path to an RO-Crate metadata JSON file or to the root directory "
    #         "of an RO-Crate, or to a ZIP-packaged RO-Crate."
    #     ),
    # )
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

    # Temporary Fix ===============================
    # The endpoint used in get_project_s3_info is currently 404 not found
    # TODO: Remove temporary fix when get_project_s3_info is working

    import five_safes_tes_workbench.helpers.project_s3_info
    from five_safes_tes_workbench.schema.config_schema import ConfigValidationModel
    from five_safes_tes_workbench.helpers.project_s3_info import ProjectS3Info

    def patched_get_project_s3_info(project_name: str, config: ConfigValidationModel) -> ProjectS3Info:
        return ProjectS3Info(output_bucket=args.s3_output_bucket, api_endpoint=args.s3_endpoint)
    five_safes_tes_workbench.helpers.project_s3_info.get_project_s3_info = patched_get_project_s3_info

    # TODO: Move the following line to the top
    from five_safes_tes_workbench.workbench import Workbench
    # End Temporary Fix ===========================

    # try:
    #     crate_metadata = load_rocrate_metadata(args.input_path)
    #     print("RO-Crate metadata loaded")
    # except (OSError, json.JSONDecodeError, ValueError) as exc:
    #     print(f"Error: {exc}", file=sys.stderr)
    #     return 1

    wb = Workbench()
    wb.validate(config_path=args.config_path)

    paths = wb.fetch_outputs(task_id=args.task_id, output_dir=args.output_dir / args.roc_name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
