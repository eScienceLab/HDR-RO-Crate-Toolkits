import pytest

from toolkits.clients.validation_client import validate_rocrate_metadata


def mock_response(json_data):
    class Response:
        def json(self):
            return json_data
        
    return Response()

def test_validate_rocrate_metadata(monkeypatch):
    response_json = {"result": "stringified json result"}
    def mock_post(*args, **kwargs):
        return mock_response(response_json)

    monkeypatch.setattr(
        "toolkits.clients.validation_client.requests.post",
        mock_post
    )

    assert validate_rocrate_metadata({}) == response_json
