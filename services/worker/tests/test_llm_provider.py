import json
from unittest.mock import MagicMock, patch

import httpx
import pytest
from docuparse_contracts import ResumeExtraction

from app.llm_provider import GroqProvider

VALID_EXTRACTION = {
    "full_name": "Jane Doe",
    "email": "jane@example.com",
    "phone": None,
    "location": "New York, NY",
    "summary": "Experienced engineer.",
    "skills": ["Python", "FastAPI"],
    "experience": [
        {
            "company": "Acme Corp",
            "title": "Engineer",
            "start": "2020",
            "end": None,
            "bullets": ["Built things"],
        }
    ],
    "education": [{"institution": "MIT", "degree": "BS CS", "year": "2019"}],
}


def _mock_response(data: dict, status_code: int = 200) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = {"choices": [{"message": {"content": json.dumps(data)}}]}
    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=mock_resp
        )
    else:
        mock_resp.raise_for_status.return_value = None
    return mock_resp


def test_extract_resume_happy_path() -> None:
    provider = GroqProvider(api_key="test-key", model="llama-3.1-8b-instant")
    with patch("app.llm_provider.httpx.post", return_value=_mock_response(VALID_EXTRACTION)):
        result = provider.extract_resume("Jane Doe resume text")
    assert isinstance(result, ResumeExtraction)
    assert result.full_name == "Jane Doe"
    assert "Python" in result.skills


def test_extract_resume_http_error_raises() -> None:
    provider = GroqProvider(api_key="test-key", model="llama-3.1-8b-instant")
    with patch("app.llm_provider.httpx.post", return_value=_mock_response({}, status_code=500)):
        with pytest.raises(httpx.HTTPStatusError):
            provider.extract_resume("some text")


def test_extract_resume_malformed_json_raises() -> None:
    provider = GroqProvider(api_key="test-key", model="llama-3.1-8b-instant")
    bad_resp = MagicMock()
    bad_resp.raise_for_status.return_value = None
    bad_resp.json.return_value = {"choices": [{"message": {"content": "not json {"}}]}
    with patch("app.llm_provider.httpx.post", return_value=bad_resp):
        with pytest.raises(Exception):
            provider.extract_resume("some text")
