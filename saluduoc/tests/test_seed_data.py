"""Invariantes del seed de establecimientos."""

import json
from collections import defaultdict
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "seed" / "establishments.json"


def test_seed_has_four_per_campus_and_three_urgent():
    records = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    assert len(records) == 76

    by_campus = defaultdict(list)
    for record in records:
        by_campus[record["sede_duoc"]].append(record)
        assert record["codigo"]
        assert record["lat"] is not None and record["lng"] is not None
        assert record["fuente"].startswith("DEIS MINSAL")

    assert len(by_campus) == 19
    for campus, items in by_campus.items():
        assert len(items) == 4, campus
        urgent = [item for item in items if item["tiene_urgencia"]]
        assert len(urgent) >= 3, f"{campus} solo tiene {len(urgent)} urgencias"


def test_seed_excludes_pediatric_and_dental():
    records = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    forbidden = ("niño", "niños", "pediátric", "maternidad", "maternal", "dental")
    for record in records:
        name = record["nombre"].lower()
        assert not any(word in name for word in forbidden), record["nombre"]
