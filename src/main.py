"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.api import admin, auth, citizen, officer, users
from src.infrastructure.config import settings
from src.infrastructure.security.trusted_proxy import TrustedProxyMiddleware

# Security review F6: interactive API docs/schema reveal the full endpoint surface (including
# admin-only routes) to anyone, unauthenticated. Disable them outside development.
_docs_enabled = settings.environment != "production"

app = FastAPI(
    title="LocalFix Authentication and RBAC",
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)

# Feature 002 BE-014/BE-015: must run before routing/rate-limiting so request.client.host is
# already corrected (for a trusted peer only) by the time any dependency reads it.
app.add_middleware(TrustedProxyMiddleware)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(citizen.router)
app.include_router(officer.router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    # Generic, non-leaking error body: never include internal detail, stack info, or secrets.
    detail = exc.detail if isinstance(exc.detail, str) else "error"
    return JSONResponse(status_code=exc.status_code, content={"error": detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    # Security review F8: use the same {"error": "..."} shape as every other error response,
    # instead of FastAPI's default verbose {"detail": [...]} (which also echoes back whatever
    # the client submitted, including for the password fields).
    return JSONResponse(status_code=422, content={"error": "validation_error"})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"error": "internal_server_error"})
