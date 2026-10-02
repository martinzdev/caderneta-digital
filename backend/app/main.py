import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import auth, clients, ledger, orders

logger = logging.getLogger("caderneta")


def create_app() -> FastAPI:
    settings = get_settings()
    docs = "/docs" if settings.enable_docs else None
    app = FastAPI(
        title="Caderneta Digital API",
        docs_url=docs,
        redoc_url=None,
        openapi_url=docs and "/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        fields = [".".join(str(p) for p in err["loc"][1:]) for err in exc.errors()]
        return JSONResponse(
            status_code=422,
            content={"detail": "Dados inválidos. Confira os campos.", "fields": fields},
        )

    @app.exception_handler(Exception)
    async def unexpected_error(_: Request, exc: Exception):
        logger.exception("unexpected error", exc_info=exc)
        return JSONResponse(
            status_code=500, content={"detail": "Não foi possível concluir. Tente novamente."}
        )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    for router in (auth.router, clients.router, ledger.router, orders.router):
        app.include_router(router)
    return app


app = create_app()
