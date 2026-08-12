import pytest
from httpx import AsyncClient

ALLOWED_ORIGIN = "http://localhost:5173"


@pytest.mark.asyncio
async def test_cors_allows_configured_frontend_origin(
    api_client: AsyncClient,
) -> None:
    response = await api_client.options(
        "/auth/login",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "content-type" in response.headers["access-control-allow-headers"].casefold()


@pytest.mark.asyncio
async def test_cors_rejects_unconfigured_origin(
    api_client: AsyncClient,
) -> None:
    response = await api_client.options(
        "/auth/login",
        headers={
            "Origin": "https://malicious.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
