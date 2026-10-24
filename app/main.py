"""Punto de entrada de SaluDuoc.

project-id: 29324fd4-f130-400e-9542-f3dcd52fb814
prd-id: 9ab3b43b-fde8-4977-b3dc-a9e57b27de7b
"""

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.core.config import settings
from app.db.session import get_db

BASE_DIR = Path(__file__).resolve().parent
IS_PROD = settings.ENV == "prod"

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Apoyo a la categorización de urgencia y monitoreo de signos vitales.",
    docs_url=None if IS_PROD else "/docs",
    redoc_url=None if IS_PROD else "/redoc",
    openapi_url=None if IS_PROD else "/openapi.json",
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Cabeceras de seguridad básicas para todas las respuestas."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("Permissions-Policy", "geolocation=(self)")
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Devuelve errores de validación sin ecoar valores sensibles (ej. contraseñas)."""
    errors = [
        {"loc": error.get("loc"), "msg": error.get("msg"), "type": error.get("type")}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content={"detail": errors}
    )


@app.get("/healthz", tags=["health"])
def healthz() -> dict[str, str]:
    """Liveness: el proceso responde."""
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/readyz", tags=["health"])
def readyz(db: Session = Depends(get_db)) -> dict[str, str]:
    """Readiness: comprueba que la base de datos responde."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from None
    return {"status": "ready"}


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request, name="index.html", context={"app_name": settings.APP_NAME}
    )


@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request, name="login.html", context={"app_name": settings.APP_NAME}
    )


@app.get("/registro", response_class=HTMLResponse, include_in_schema=False)
def register_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request, name="register.html", context={"app_name": settings.APP_NAME}
    )
