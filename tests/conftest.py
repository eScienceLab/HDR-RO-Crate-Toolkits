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
