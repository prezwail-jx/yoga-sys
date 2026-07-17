import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.endpoints import auth, card_products, member_cards, members, transactions
from app.api.routes import timeline, writeoff
from app.api.middleware.audit_rejections import RejectedAuditMiddleware
from app.api.middleware.request_context import RequestContextMiddleware

def create_app() -> FastAPI:
    app = FastAPI(title="Yoga Sys API", version="0.2.0")
    app.add_middleware(RejectedAuditMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=[origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    @app.exception_handler(Exception)
    async def handle_exception(request: Request, _: Exception):
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error", "traceId": getattr(request.state, "trace_id", None)})
    @app.get("/healthz", tags=["System"])
    def healthz() -> dict[str, str]:
        return {"status": "ok"}
    app.include_router(auth.router, prefix="/auth", tags=["Auth"])
    app.include_router(members.router, prefix="/members", tags=["Members"])
    app.include_router(card_products.router, prefix="/card-products", tags=["Card Products"])
    app.include_router(transactions.router, tags=["Transactions"])
    app.include_router(member_cards.router, tags=["Member Cards"])
    app.include_router(writeoff.router, tags=["WriteOff"])
    app.include_router(timeline.router, tags=["Timeline"])
    return app
app = create_app()
