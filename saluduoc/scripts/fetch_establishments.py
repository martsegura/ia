#!/usr/bin/env python3
"""Genera el seed de establecimientos a partir del dataset DEIS/MINSAL.

Fuente: https://datos.gob.cl/dataset/establecimientos-de-salud-vigentes
Snapshot: 2026-10-20 (licencia CC0).

Para cada sede de Duoc UC se seleccionan hasta 4 establecimientos cercanos:
- al menos 3 con servicio de urgencia (hospital, clínica, SAPU, SAR, SUR);
- el resto se completa con los más cercanos (CESFAM u otros).
Se excluyen establecimientos pediátricos, maternales y dentales porque el MVP es
atención médica adulta general.
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
MAX_RADIUS_KM = 25.0
PER_CAMPUS = 4
MIN_URGENT_PER_CAMPUS = 3

URGENT_TYPES = {
    "Hospital",
    "Clínica",
    "Servicio de Atención Primaria de Urgencia (SAPU)",
    "Servicio de Atención Primaria de Urgencia de Alta Resolutividad (SAR)",
    "Servicio de Urgencia Rural (SUR)",
}
EXCLUDED_KEYWORDS = (
    "niño",
    "niños",
    "pediátric",
    "maternidad",
    "maternal",
    "dental",
)


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


def is_urgent(record: dict[str, str]) -> bool:
    return clean(record.get("TieneServicioUrgencia")).upper() == "SI"


def is_pediatric(record: dict[str, str]) -> bool:
    name = clean(record.get("EstablecimientoGlosa")).lower()
    return any(keyword in name for keyword in EXCLUDED_KEYWORDS)


def fallback_priority(record: dict[str, str]) -> int:
    kind = clean(record.get("TipoEstablecimientoGlosa"))
    if kind == "Centro de Salud Familiar (CESFAM)":
        return 0
    if kind == "Centro de Salud Privado":
        return 2
    return 1


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
        if is_pediatric(row):
            continue
        rows.append(row)

    selected: list[dict] = []
    used_codes: set[str] = set()
    urgent_by_campus: dict[str, int] = {}

    for campus in campuses:
        candidates: list[tuple[int, float, str, dict[str, str]]] = []
        for row in rows:
            lat = parse_float(row.get("Latitud"))
            lon = parse_float(row.get("Longitud"))
            assert lat is not None and lon is not None
            distance = haversine(campus["lat"], campus["lng"], lat, lon)
            if distance > MAX_RADIUS_KM:
                continue
            code = clean(row.get("EstablecimientoCodigo")) or (
                f"{clean(row.get('EstablecimientoGlosa'))}-{lat:.5f}-{lon:.5f}"
            )
            if code in used_codes:
                continue
            candidates.append((fallback_priority(row), distance, code, row))

        urgent = sorted(
            (item for item in candidates if is_urgent(item[3])), key=lambda item: item[1]
        )
        other = sorted(
            (item for item in candidates if not is_urgent(item[3])),
            key=lambda item: (item[0], item[1]),
        )

        chosen: list[tuple[int, float, str, dict[str, str]]] = []
        chosen.extend(urgent[:MIN_URGENT_PER_CAMPUS])
        for item in other + urgent[MIN_URGENT_PER_CAMPUS:]:
            if len(chosen) >= PER_CAMPUS:
                break
            if item not in chosen:
                chosen.append(item)

        campus_records = []
        for _, distance, code, row in chosen:
            used_codes.add(code)
            campus_records.append(
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
                    "tiene_urgencia": is_urgent(row),
                    "servicios": [clean(row.get("TipoUrgencia"))]
                    if clean(row.get("TipoUrgencia")) not in ("", "No Aplica")
                    else [],
                    "sede_duoc": campus["nombre"],
                    "distancia_km": round(distance, 2),
                    "fuente": SOURCE,
                    "fecha_snapshot": SNAPSHOT,
                }
            )

        selected.extend(campus_records)
        urgent_count = sum(1 for record in campus_records if record["tiene_urgencia"])
        urgent_by_campus[campus["nombre"]] = urgent_count
        print(
            f"{campus['nombre']}: {len(campus_records)} establecimientos "
            f"({urgent_count} urgentes)"
        )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(selected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nTotal: {len(selected)} establecimientos -> {OUTPUT_FILE}")

    incomplete = {
        campus: count
        for campus, count in urgent_by_campus.items()
        if count < MIN_URGENT_PER_CAMPUS
    }
    if incomplete:
        print(
            f"\nADVERTENCIA: estas sedes no alcanzan {MIN_URGENT_PER_CAMPUS} urgencias "
            f"en {MAX_RADIUS_KM:.0f} km:"
        )
        for campus, count in incomplete.items():
            print(f"  - {campus}: {count}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
