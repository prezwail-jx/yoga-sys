from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.middleware.request_context import RequestContextMiddleware
from app.api.routes.contracts_stub import router as contracts_stub_router


def create_app() -> FastAPI:
    app = FastAPI(title="Yoga Sys API", version="0.1.0")
    app.add_middleware(RequestContextMiddleware)

    @app.exception_handler(Exception)
    async def handle_exception(_: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error", "error": str(exc)},
        )

    @app.get("/healthz", tags=["System"])
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(contracts_stub_router)
    return app


app = create_app()
