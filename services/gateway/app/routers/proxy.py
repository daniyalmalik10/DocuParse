import httpx
from fastapi import APIRouter, Depends, Request, Response

from app.config import Settings, get_settings
from app.dependencies import get_current_user_id

router = APIRouter()

_HOP_BY_HOP = frozenset(
    ["host", "content-length", "transfer-encoding", "connection", "content-encoding"]
)

_http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient()
    return _http_client


async def proxy_request(
    path: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    settings: Settings = Depends(get_settings),
    client: httpx.AsyncClient = Depends(get_http_client),
) -> Response:
    target_url = f"{settings.document_service_url}/documents/{path}"

    forward_headers = {k: v for k, v in request.headers.items() if k.lower() not in _HOP_BY_HOP}
    forward_headers["x-user-id"] = user_id

    body = await request.body()

    upstream = await client.request(
        method=request.method,
        url=target_url,
        headers=forward_headers,
        content=body,
        params=dict(request.query_params),
    )

    response_headers = {k: v for k, v in upstream.headers.items() if k.lower() not in _HOP_BY_HOP}

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )


for _method in ("GET", "POST", "PUT", "PATCH", "DELETE"):
    router.add_api_route(
        "/api/documents/{path:path}",
        proxy_request,
        methods=[_method],
    )
