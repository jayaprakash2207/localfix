"""Security review F6: /docs, /redoc, /openapi.json must be disabled when environment=production
and remain available in development.

docs_url/redoc_url/openapi_url are baked into the FastAPI app at construction time (src/main.py
module import), not re-evaluated per request - so testing the production case requires
reloading src.main under a patched setting and building a dedicated client against the
freshly-constructed app, without disturbing the shared `app` object every other test's `client`
fixture already imported (reloading src.main does not retroactively change an already-bound
`from src.main import app` reference elsewhere, so this is safe).
"""

from __future__ import annotations

import importlib

import pytest
from httpx import ASGITransport, AsyncClient

from src.infrastructure.config import settings


async def test_docs_available_in_development(client: AsyncClient):
    assert (await client.get("/docs")).status_code == 200
    assert (await client.get("/openapi.json")).status_code == 200


async def test_docs_disabled_in_production(monkeypatch: pytest.MonkeyPatch):
    import src.main as main_module

    monkeypatch.setattr(settings, "environment", "production")
    reloaded = importlib.reload(main_module)
    try:
        transport = ASGITransport(app=reloaded.app)
        async with AsyncClient(transport=transport, base_url="http://test") as prod_client:
            assert (await prod_client.get("/docs")).status_code == 404
            assert (await prod_client.get("/redoc")).status_code == 404
            assert (await prod_client.get("/openapi.json")).status_code == 404
    finally:
        # Restore the module-level `app` to a development-configured instance so it doesn't
        # leak a production-mode app into sys.modules for any later import of src.main. Not
        # DB-touching by design (this reloaded app has no dependency_overrides wired to the
        # test database), so this test deliberately only exercises the docs routes.
        monkeypatch.undo()
        importlib.reload(main_module)
