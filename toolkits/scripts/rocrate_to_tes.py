import argparse
import json
import sys

from toolkits.clients.tes_client import load_rocrate_metadata, extract_tes_message
from toolkits.services.validation_service import is_rocrate_metadata_valid


def parse_args(argv=None):
    """Parse command-line arguments for the RO-Crate to TES extractor."""

    parser = argparse.ArgumentParser(
        description="Extract a TES message embedded in RO-Crate metadata."
    )
    parser.add_argument(
        "input_path",
        help=(
            "Path to an RO-Crate metadata JSON file or to the root directory "
            "of an RO-Crate, or to a ZIP-packaged RO-Crate."
        ),
    )
    return parser.parse_args(argv)


def main(argv=None):
    """Run the CLI and print the extracted TES message as formatted JSON.

    Returns:
        int: `0` on success, `1` if the metadata file cannot be read, parsed,
        or does not contain exactly one TES payload.
    """

    args = parse_args(argv)

    try:
        crate_metadata = load_rocrate_metadata(args.input_path)
        print(f"Validation passed: {is_rocrate_metadata_valid(json.dumps(crate_metadata))}")
        tes_message = extract_tes_message(crate_metadata)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    
    

    json.dump(tes_message, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
