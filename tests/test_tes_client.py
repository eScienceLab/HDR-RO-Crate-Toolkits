import json
import pytest
import requests

from unittest.mock import Mock, patch

from toolkits.clients.tes_client import create_tes_task


MOCK_API_URL = "https://submission.layer.api"
MOCK_API_TOKEN = "SECRET"
TES_MSG_DICT = {'state': 0, 'name': 'Hello World'}

@patch("toolkits.clients.tes_client.requests.post")
def test_create_tes_task(mock_post):
    mock_response = Mock()
    mock_response.json.return_value = {"$id": "1", "id": "1"}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    with patch("toolkits.clients.tes_client.TASK_SERVICE_API_URL", MOCK_API_URL), \
         patch("toolkits.clients.tes_client.TASK_SUBMISSION_API_TOKEN", MOCK_API_TOKEN):
        response_json = create_tes_task(TES_MSG_DICT)

    # requests.post should be called with the following
    url = MOCK_API_URL + "/v1/tasks"
    headers = {
        "accept": "application/json", 
        "Content-Type": "application/json-patch+json", 
        "Authorization": "Bearer " + MOCK_API_TOKEN
    }
    payload = json.dumps(TES_MSG_DICT)

    mock_post.assert_called_once_with(url, headers=headers, data=payload)
    assert response_json == {"$id": "1", "id": "1"}

def test_create_tes_task_non_dict_input():
    with pytest.raises(TypeError, match="tes_message must be a dictionary"):
        create_tes_task("not dict")

@patch("toolkits.clients.tes_client.requests.post")
def test_create_tes_task_http_error(mock_post):
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError
    mock_post.return_value = mock_response

    with pytest.raises(requests.exceptions.HTTPError):
        create_tes_task(TES_MSG_DICT)

@patch("toolkits.clients.tes_client.requests.post")
def test_create_tes_task_json_error(mock_post):
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.side_effect = requests.exceptions.JSONDecodeError("Expecting value", "", 0)
    mock_post.return_value = mock_response

    with pytest.raises(requests.exceptions.JSONDecodeError, 
                       match="Expecting value: line 1 column 1 \\(char 0\\)"):
        create_tes_task(TES_MSG_DICT)