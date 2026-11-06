import os

import pytest


# Mock environment variables
os.environ["CRATEY_VALIDATOR_API_URL"] = "https://cratey.validator.api"


@pytest.fixture
def mock_wb_config(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(
        """
        config:
          project: "Testing"
          tes_base_url: "https://submission.layer.api"
          minio_sts_endpoint: "https://minio.api/sts"
          minio_endpoint: "https://minio.api"
          minio_output_bucket: "11111outputtre"
          tres:
            - "DEMO"
        auth:
          access_token: "SECRET"
        """
    )
    return str(path)


# Workbench configs that parse as YAML but fail the Workbench's own validators,
# which raise WorkbenchError subclasses rather than ValueError.
WORKBENCH_INVALID_CONFIGS = {
    "empty_tres": 'config:\n  project: "Testing"\n  tes_base_url: "https://submission.layer.api"\n  minio_sts_endpoint: "https://minio.api/sts"\n  minio_endpoint: "https://minio.api"\n  minio_output_bucket: "11111outputtre"\n  tres: []\nauth:\n  access_token: "SECRET"\n',
    "incomplete_auth": 'config:\n  project: "Testing"\n  tes_base_url: "https://submission.layer.api"\n  minio_sts_endpoint: "https://minio.api/sts"\n  minio_endpoint: "https://minio.api"\n  minio_output_bucket: "11111outputtre"\n  tres: ["DEMO"]\nauth:\n  username: "user"\n',
}


@pytest.fixture(params=sorted(WORKBENCH_INVALID_CONFIGS), ids=str)
def invalid_wb_config(tmp_path, request):
    """A Workbench config file rejected by the Workbench's own validators."""

    path = tmp_path / "invalid-config.yaml"
    path.write_text(WORKBENCH_INVALID_CONFIGS[request.param])
    return str(path)
