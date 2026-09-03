import argparse
import json
import logging
import sys
import uuid

from pathlib import Path
# from five_safes_tes_workbench.workbench import Workbench
from fivesafe_crate_py import FiveSafesCrate
from rocrate.model.contextentity import ContextEntity

from toolkits.clients.tes_client import is_tes_message_entity

logging.disable(logging.INFO)


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
        print("RO-Crate loaded")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        matches = [entity for entity in crate.data_entities if is_tes_message_entity(entity.properties())]
        if not matches:
            raise ValueError("No TES message found in RO-Crate metadata.")
        if len(matches) > 1:
            raise ValueError("Multiple TES message candidates found in RO-Crate metadata.")
        tes_msg_entity = matches[0]
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    wb = Workbench()
    wb.validate(config_path=args.config_path)

    roc_output_dir = args.output_dir / args.roc_name
    paths_dict = wb.fetch_outputs(task_id=args.task_id, output_dir=roc_output_dir)

    if paths_dict:
        result_entities = []
        paths = [path for path_list in paths_dict.values() for path in path_list]
        for path in paths:
            relative_path = path.relative_to(roc_output_dir)
            result_entity = crate.add_file(path.as_posix(), relative_path.as_posix())
            result_entities.append(result_entity)

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
        crate.write(roc_output_dir)
    else:
        # TODO: In progress or does not exist
        pass
    print(f"RO-Crate {args.roc_name} created at {args.output_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
