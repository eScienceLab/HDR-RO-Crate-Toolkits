import os 

from dotenv import load_dotenv

load_dotenv()

def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

CRATEY_VALIDATOR_API_URL = _get_required_env("CRATEY_VALIDATOR_API_URL")
TASK_SERVICE_API_URL = _get_required_env("TASK_SERVICE_API_URL")
TASK_SUBMISSION_API_TOKEN = _get_required_env("TASK_SUBMISSION_API_TOKEN")

ROCRATE_METADATA_FILENAME = "ro-crate-metadata.json"

TES_TASK_SCHEMA_ID = (
    "https://ga4gh.github.io/task-execution-schemas/openapi/"
    "task_execution_service.openapi.yaml#/components/schemas/tesTask"
)
