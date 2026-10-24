#!/usr/bin/env python3
"""Genera el seed de establecimientos a partir del dataset DEIS/MINSAL.

Fuente: https://datos.gob.cl/dataset/establecimientos-de-salud-vigentes
Snapshot: 2026-10-20 (licencia CC0).

Para cada sede de Duoc UC en data/campuses.json se seleccionan hasta 4
establecimientos cercanos, priorizando aquellos con servicio de urgencia.
El resultado se guarda en data/seed/establishments.json.
"""

from __future__ import annotations

import csv
import io
import json
import math
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMPUSES_FILE = ROOT / "data" / "campuses.json"
OUTPUT_FILE = ROOT / "data" / "seed" / "establishments.json"
CACHE_FILE = ROOT / "data" / "seed" / "establecimientos_deis_20261020.csv"

DATASET_URL = (
    "https://datos.gob.cl/dataset/3bf4cf7c-f638-4735-9a01-f65faae4beca/"
    "resource/2c44d782-3365-44e3-aefb-2c8b8363a1bc/download/establecimientos_20261020.csv"
)
SNAPSHOT = "2026-10-20"
SOURCE = "DEIS MINSAL datos.gob.cl (snapshot 2026-10-20)"
EARTH_RADIUS_KM = 6371.0
RADII_KM = (3.0, 6.0, 12.0, 25.0)
PER_CAMPUS = 4

URGENT_TYPES = {
    "Hospital",
    "Clínica",
    "Servicio de Atención Primaria de Urgencia (SAPU)",
    "Servicio de Atención Primaria de Urgencia de Alta Resolutividad (SAR)",
    "Servicio de Urgencia Rural (SUR)",
}


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def download_csv() -> str:
    if CACHE_FILE.exists():
        return CACHE_FILE.read_text(encoding="utf-8-sig")
    request = urllib.request.Request(DATASET_URL, headers={"User-Agent": "SaluDuoc-Prototype/0.1"})
    with urllib.request.urlopen(request, timeout=180) as response:  # noqa: S310
        content = response.read().decode("utf-8-sig")
    CACHE_FILE.write_text(content, encoding="utf-8")
    return content


def clean(value: str | None) -> str:
    return (value or "").strip()


def parse_float(value: str | None) -> float | None:
    try:
        number = float(clean(value))
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def priority(record: dict[str, str]) -> int:
    kind = clean(record.get("TipoEstablecimientoGlosa"))
    urgent = clean(record.get("TieneServicioUrgencia")).upper() == "SI"
    if urgent and kind in URGENT_TYPES:
        return 0
    if kind == "Centro de Salud Familiar (CESFAM)":
        return 1
    if urgent:
        return 2
    if kind == "Centro de Salud Privado":
        return 3
    return 4


def main() -> None:
    campuses = json.loads(CAMPUSES_FILE.read_text(encoding="utf-8"))
    reader = csv.DictReader(io.StringIO(download_csv()), delimiter=";")

    rows: list[dict[str, str]] = []
    for row in reader:
        estado = clean(row.get("EstadoFuncionamiento"))
        if not estado or "Cerrado" in estado:
            continue
        if parse_float(row.get("Latitud")) is None or parse_float(row.get("Longitud")) is None:
            continue
        rows.append(row)

    selected: list[dict] = []
    used_codes: set[str] = set()

    for campus in campuses:
        chosen: list[dict] = []
        for radius in RADII_KM:
            candidates = []
            for row in rows:
                lat = parse_float(row.get("Latitud"))
                lon = parse_float(row.get("Longitud"))
                assert lat is not None and lon is not None
                distance = haversine(campus["lat"], campus["lng"], lat, lon)
                if distance > radius:
                    continue
                code = clean(row.get("EstablecimientoCodigo")) or (
                    f"{clean(row.get('EstablecimientoGlosa'))}-{lat:.5f}-{lon:.5f}"
                )
                if code in used_codes:
                    continue
                candidates.append((priority(row), distance, code, row))

            candidates.sort(key=lambda item: (item[0], item[1]))
            for _, distance, code, row in candidates:
                if code in used_codes:
                    continue
                used_codes.add(code)
                chosen.append(
                    {
                        "codigo": code,
                        "nombre": clean(row.get("EstablecimientoGlosa")),
                        "tipo": clean(row.get("TipoEstablecimientoGlosa")),
                        "direccion": " ".join(
                            part
                            for part in (
                                clean(row.get("TipoViaGlosa")),
                                clean(row.get("NombreVia")),
                                clean(row.get("Numero")),
                            )
                            if part
                        ),
                        "comuna": clean(row.get("ComunaGlosa")),
                        "region": clean(row.get("RegionGlosa")),
                        "lat": parse_float(row.get("Latitud")),
                        "lng": parse_float(row.get("Longitud")),
                        "telefono": clean(row.get("TelefonoMovil_TelefonoFijo")),
                        "tiene_urgencia": clean(row.get("TieneServicioUrgencia")).upper() == "SI",
                        "servicios": [clean(row.get("TipoUrgencia"))]
                        if clean(row.get("TipoUrgencia")) not in ("", "No Aplica")
                        else [],
                        "sede_duoc": campus["nombre"],
                        "distancia_km": round(distance, 2),
                        "fuente": SOURCE,
                        "fecha_snapshot": SNAPSHOT,
                    }
                )
                if len(chosen) >= PER_CAMPUS:
                    break
            if len(chosen) >= PER_CAMPUS:
                break

        selected.extend(chosen)
        print(f"{campus['nombre']}: {len(chosen)} establecimientos")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(selected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nTotal: {len(selected)} establecimientos -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
