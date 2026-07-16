from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.audit import record_audit
from app.infra.db.session import SessionLocal


class RejectedAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        user = getattr(request.state, "current_user", None)
        if response.status_code == 403 and user is not None and request.method in {"POST", "PATCH", "PUT", "DELETE"}:
            parts = [part for part in request.url.path.split("/") if part]
            object_type = parts[0] if parts else "unknown"
            object_id = parts[1] if len(parts) > 1 else "collection"
            with SessionLocal() as session:
                record_audit(
                    session,
                    trace_id=getattr(request.state, "trace_id", "unknown"),
                    action=f"{request.method.lower()}_{object_type}",
                    user=user,
                    object_type=object_type,
                    object_id=object_id,
                    result="rejected",
                    reason="Forbidden",
                )
                session.commit()
        return response
