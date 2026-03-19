import argparse
import json

from toolkits.clients.validation_client import validate_rocrate_metadata

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file_path", help="path to RO-Crate metadata file")
    args = parser.parse_args()

    with open(args.file_path, "r") as f:
        data = json.dumps(json.load(f))

    result = validate_rocrate_metadata(data).get("result", None)
    result_json = json.loads(result)
    passed = result_json.get("passed", False)
    print(f"Validation passed: {passed}")

if __name__ == "__main__":
    main()