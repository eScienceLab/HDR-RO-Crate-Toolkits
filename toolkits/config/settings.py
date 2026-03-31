import os 

from dotenv import load_dotenv

load_dotenv()

CRATEY_VALIDATOR_API_URL = os.getenv("CRATEY_VALIDATOR_API_URL")
TASK_SERVICE_API_URL = os.getenv("TASK_SERVICE_API_URL")
TASK_SUBMISSION_API_TOKEN = os.getenv("TASK_SUBMISSION_API_TOKEN")

ROCRATE_METADATA_FILENAME = "ro-crate-metadata.json"

TES_TASK_SCHEMA_ID = (
    "https://ga4gh.github.io/task-execution-schemas/openapi/"
    "task_execution_service.openapi.yaml#/components/schemas/tesTask"
)
