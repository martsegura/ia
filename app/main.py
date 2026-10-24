"""Punto de entrada de SaluDuoc.

project-id: 29324fd4-f130-400e-9542-f3dcd52fb814
prd-id: 9ab3b43b-fde8-4977-b3dc-a9e57b27de7b
"""

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import load_user_from_token
from app.api.v1.auth import router as auth_router
from app.api.v1.establishments import router as establishments_router
from app.api.v1.queue import router as queue_router
from app.api.v1.triage import router as triage_router
from app.api.v1.users import router as users_router
from app.api.v1.vitals import router as vitals_router
from app.core.config import settings
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.establishment import Establishment
from app.models.normal_range import NormalRange
from app.models.user import User
from app.services import consultation, queue_service
from app.services.triage import SUPPORTED_SYMPTOMS

BASE_DIR = Path(__file__).resolve().parent
IS_PROD = settings.ENV == "prod"

ROLE_HOME = {
    UserRole.PATIENT: "/paciente",
    UserRole.DOCTOR: "/medico",
    UserRole.ADMIN: "/admin",
}

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
app.include_router(vitals_router, prefix="/api/v1")
app.include_router(triage_router, prefix="/api/v1")
app.include_router(establishments_router, prefix="/api/v1")
app.include_router(queue_router, prefix="/api/v1")


def home_for(user: User) -> str:
    return ROLE_HOME.get(user.role, "/")


def base_context(request: Request, user: User | None = None) -> dict:
    return {
        "app_name": settings.APP_NAME,
        "user": user,
        "home_path": home_for(user) if user else None,
        "show_demo": settings.ENV in ("dev", "test"),
    }


def require_page_user(request: Request, db: Session, *roles: UserRole):
    """Devuelve (user, redirect). Si no hay sesión o el rol no corresponde, redirige."""
    user = load_user_from_token(request, db)
    if user is None:
        return None, RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    if roles and user.role not in roles:
        return None, RedirectResponse(home_for(user), status_code=status.HTTP_303_SEE_OTHER)
    return user, None


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
def index(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    user = load_user_from_token(request, db)
    return templates.TemplateResponse(
        request=request, name="index.html", context=base_context(request, user)
    )


@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page(request: Request, db: Session = Depends(get_db)):
    user = load_user_from_token(request, db)
    if user is not None:
        return RedirectResponse(home_for(user), status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request, name="login.html", context=base_context(request)
    )


@app.get("/registro", response_class=HTMLResponse, include_in_schema=False)
def register_page(request: Request, db: Session = Depends(get_db)):
    user = load_user_from_token(request, db)
    if user is not None:
        return RedirectResponse(home_for(user), status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request, name="register.html", context=base_context(request)
    )


@app.get("/dashboard", include_in_schema=False)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_page_user(request, db)
    if redirect is not None:
        return redirect
    return RedirectResponse(home_for(user), status_code=status.HTTP_303_SEE_OTHER)


@app.get("/paciente", response_class=HTMLResponse, include_in_schema=False)
def patient_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_page_user(request, db, UserRole.PATIENT)
    if redirect is not None:
        return redirect
    profile = user.patient_profile
    latest = consultation.latest_assessment(db, user)
    queue_entry = queue_service.entry_for_patient(db, user.id)
    establishments = db.scalars(
        select(Establishment)
        .where(Establishment.is_active.is_(True))
        .order_by(Establishment.nombre)
    ).all()
    context = base_context(request, user) | {
        "profile": profile,
        "latest": consultation.assessment_out(db, latest) if latest else None,
        "queue_entry": queue_service.serialize_entry(db, queue_entry) if queue_entry else None,
        "history": consultation.vitals_history(db, user, limit=5),
        "symptoms": SUPPORTED_SYMPTOMS,
        "establishments": establishments,
    }
    return templates.TemplateResponse(request=request, name="paciente.html", context=context)


@app.get("/medico", response_class=HTMLResponse, include_in_schema=False)
def doctor_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_page_user(request, db, UserRole.DOCTOR)
    if redirect is not None:
        return redirect
    doctor_profile = user.doctor_profile
    establishment = doctor_profile.establecimiento if doctor_profile else None
    queue_entries = (
        queue_service.list_queue(db, establishment.id) if establishment else []
    )
    context = base_context(request, user) | {
        "doctor_profile": doctor_profile,
        "establishment": establishment,
        "queue_entries": queue_entries,
        "queue_count": len(queue_entries),
        "critical_count": sum(
            1 for entry in queue_entries if entry.category in ("C1", "C2")
        ),
        "in_attention_count": sum(
            1 for entry in queue_entries if entry.status == "in_attention"
        ),
    }
    return templates.TemplateResponse(request=request, name="medico.html", context=context)


@app.get("/admin", response_class=HTMLResponse, include_in_schema=False)
def admin_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_page_user(request, db, UserRole.ADMIN)
    if redirect is not None:
        return redirect
    stats = {
        "users": db.scalar(select(func.count()).select_from(User)) or 0,
        "establishments": db.scalar(
            select(func.count()).select_from(Establishment).where(Establishment.is_active.is_(True))
        )
        or 0,
        "ranges": db.scalar(select(func.count()).select_from(NormalRange)) or 0,
    }
    establishments = db.scalars(
        select(Establishment)
        .where(Establishment.is_active.is_(True))
        .order_by(Establishment.nombre)
        .limit(10)
    ).all()
    users = db.scalars(select(User).order_by(User.created_at.desc()).limit(10)).all()
    context = base_context(request, user) | {
        "stats": stats,
        "establishments": establishments,
        "users": users,
    }
    return templates.TemplateResponse(request=request, name="admin.html", context=context)
