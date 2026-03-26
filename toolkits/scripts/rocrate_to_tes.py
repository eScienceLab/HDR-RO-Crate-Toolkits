import argparse
import json

from toolkits.services.validation_service import is_rocrate_metadata_valid

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file_path", help="path to RO-Crate metadata file")
    args = parser.parse_args()

    with open(args.file_path, "r") as f:
        data = json.dumps(json.load(f))

    print(f"Validation passed: {is_rocrate_metadata_valid(data)}")

if __name__ == "__main__":
    main()