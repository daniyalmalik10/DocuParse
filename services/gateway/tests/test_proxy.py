from unittest.mock import AsyncMock, MagicMock

import httpx
from bson import ObjectId

from app.jwt_utils import sign_access_token


def _make_upstream_response(status_code: int = 200, content: bytes = b"ok") -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.content = content
    resp.headers = httpx.Headers({"content-type": "application/json"})
    return resp


class TestProxy:
    async def test_get_forwards_to_document_service(self, client, mock_http_client, test_settings):
        user_id = str(ObjectId())
        access_token = sign_access_token(user_id, test_settings)
        mock_http_client.request = AsyncMock(
            return_value=_make_upstream_response(200, b'{"items":[]}')
        )

        resp = await client.get(
            "/api/documents/", headers={"Authorization": f"Bearer {access_token}"}
        )

        assert resp.status_code == 200
        call_kwargs = mock_http_client.request.call_args
        assert call_kwargs.kwargs["method"] == "GET"
        assert "document-test:8001" in call_kwargs.kwargs["url"]
        assert "/documents/" in call_kwargs.kwargs["url"]

    async def test_injects_x_user_id_header(self, client, mock_http_client, test_settings):
        user_id = str(ObjectId())
        access_token = sign_access_token(user_id, test_settings)
        mock_http_client.request = AsyncMock(return_value=_make_upstream_response())

        await client.get("/api/documents/", headers={"Authorization": f"Bearer {access_token}"})

        forwarded_headers = mock_http_client.request.call_args.kwargs["headers"]
        assert forwarded_headers.get("x-user-id") == user_id

    async def test_no_auth_returns_401(self, client, mock_http_client):
        resp = await client.get("/api/documents/")
        assert resp.status_code == 401
        mock_http_client.request.assert_not_called()

    async def test_forwards_query_params(self, client, mock_http_client, test_settings):
        user_id = str(ObjectId())
        access_token = sign_access_token(user_id, test_settings)
        mock_http_client.request = AsyncMock(return_value=_make_upstream_response())

        await client.get(
            "/api/documents/?page=2&limit=10",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        call_kwargs = mock_http_client.request.call_args.kwargs
        assert call_kwargs["params"].get("page") == "2"
        assert call_kwargs["params"].get("limit") == "10"

    async def test_forwards_request_body(self, client, mock_http_client, test_settings):
        user_id = str(ObjectId())
        access_token = sign_access_token(user_id, test_settings)
        mock_http_client.request = AsyncMock(return_value=_make_upstream_response(201, b"{}"))
        body = b'{"filename": "resume.pdf"}'

        await client.post(
            "/api/documents/",
            content=body,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )

        call_kwargs = mock_http_client.request.call_args.kwargs
        assert call_kwargs["content"] == body

    async def test_returns_upstream_status_code(self, client, mock_http_client, test_settings):
        user_id = str(ObjectId())
        access_token = sign_access_token(user_id, test_settings)
        mock_http_client.request = AsyncMock(
            return_value=_make_upstream_response(404, b'{"detail":"not found"}')
        )

        resp = await client.get(
            "/api/documents/nonexistent",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert resp.status_code == 404

    async def test_url_prefix_stripped(self, client, mock_http_client, test_settings):
        user_id = str(ObjectId())
        access_token = sign_access_token(user_id, test_settings)
        mock_http_client.request = AsyncMock(return_value=_make_upstream_response())

        await client.get(
            "/api/documents/abc123/status",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        url = mock_http_client.request.call_args.kwargs["url"]
        assert "/documents/abc123/status" in url
        assert "/api/documents" not in url
