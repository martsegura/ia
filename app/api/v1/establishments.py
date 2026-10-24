"""Listado de establecimientos ordenado por distancia."""

from __future__ import annotations

import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.establishment import Establishment
from app.models.user import User
from app.schemas.vitals import EstablishmentOut

router = APIRouter(prefix="/establishments", tags=["establishments"])


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return 2 * 6371.0 * math.asin(math.sqrt(a))


@router.get("", response_model=list[EstablishmentOut])
def list_establishments(
    lat: float | None = Query(default=None, ge=-90, le=90),
    lng: float | None = Query(default=None, ge=-180, le=180),
    emergency: bool | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[EstablishmentOut]:
    query = select(Establishment).where(Establishment.is_active.is_(True))
    if emergency is not None:
        query = query.where(Establishment.tiene_urgencia.is_(emergency))
    items = db.scalars(query.order_by(Establishment.nombre).limit(limit)).all()

    results: list[EstablishmentOut] = []
    for item in items:
        distance = None
        if lat is not None and lng is not None and item.lat is not None and item.lng is not None:
            distance = round(haversine(lat, lng, item.lat, item.lng), 2)
        results.append(
            EstablishmentOut(
                id=item.id,
                nombre=item.nombre,
                tipo=item.tipo,
                direccion=item.direccion,
                comuna=item.comuna,
                region=item.region,
                lat=item.lat,
                lng=item.lng,
                telefono=item.telefono,
                tiene_urgencia=item.tiene_urgencia,
                sede_duoc=item.sede_duoc,
                distance_km=distance,
            )
        )

    if lat is not None and lng is not None:
        results.sort(key=lambda item: (item.distance_km is None, item.distance_km or 0))
    return results
