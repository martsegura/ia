"""Motor de triage C1-C5 basado en rangos MINSAL configurables.

Dos capas:
1. Banderas rojas que fuerzan C1 o C2.
2. Severidad de cada signo vital + síntomas + edad/comorbilidades para C3-C5.

El resultado es explicable: incluye reglas activadas, puntaje y justificación.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.models.normal_range import NormalRange

COLORS = {"C1": "rojo", "C2": "rojo", "C3": "amarillo", "C4": "verde", "C5": "verde"}
PRIORITY = {"C1": 1, "C2": 2, "C3": 3, "C4": 4, "C5": 5}
SEVERITY_POINTS = {"normal": 0, "leve": 1, "moderado": 2, "critico": 3}
SEVERITY_BASE = {"critico": "C2", "moderado": "C3", "leve": "C4", "normal": "C5"}

C1_SYMPTOMS = {
    "Pérdida de conciencia",
    "Convulsión",
    "Sangrado abundante",
    "Dificultad respiratoria severa",
}
C2_SYMPTOMS = {
    "Dolor torácico",
    "Dificultad para respirar",
    "Signos de ACV",
    "Síncope",
    "Anafilaxia",
}
MODERATE_SYMPTOMS = {
    "Fiebre alta",
    "Vómitos persistentes",
    "Mareo",
    "Palpitaciones",
}
SUPPORTED_SYMPTOMS = sorted(C1_SYMPTOMS | C2_SYMPTOMS | MODERATE_SYMPTOMS | {"Ninguno"})

METRIC_LABELS = {
    "heart_rate_bpm": ("FC", "lpm"),
    "systolic_mmhg": ("Presión sistólica", "mmHg"),
    "diastolic_mmhg": ("Presión diastólica", "mmHg"),
    "spo2_pct": ("SpO2", "%"),
}


@dataclass
class TriageResult:
    category: str
    color: str
    score: float
    triggered_rules: list[dict[str, Any]] = field(default_factory=list)
    rationale: str = ""
    algorithm_version: str = "v1"
    ranges_version: str = "v1"


def classify_value(value: float, band: NormalRange) -> str:
    """Clasifica un valor según los límites de una banda versionada."""
    if band.critical_low is not None and value < band.critical_low:
        return "critico"
    if band.moderate_low is not None and value < band.moderate_low:
        return "moderado"
    if band.mild_low is not None and value < band.mild_low:
        return "leve"
    if band.normal_min is not None and value < band.normal_min:
        return "leve"

    if band.critical_high is not None and value >= band.critical_high:
        return "critico"
    if band.mild_high is not None and value > band.mild_high:
        return "moderado"
    if band.normal_max is not None and value > band.normal_max:
        return "leve"
    return "normal"


def calculate_age(birth_date: date | None) -> int | None:
    if birth_date is None:
        return None
    today = date.today()
    return (
        today.year
        - birth_date.year
        - ((today.month, today.day) < (birth_date.month, birth_date.day))
    )


def assess(
    *,
    heart_rate_bpm: int | None,
    systolic_mmhg: int | None,
    diastolic_mmhg: int | None,
    spo2_pct: int | None,
    symptoms: list[str],
    pain_scale: int | None,
    age: int | None,
    comorbidities: list[str],
    ranges: dict[str, NormalRange],
) -> TriageResult:
    rules: list[dict[str, Any]] = []
    rationale: list[str] = []
    c1_triggered = False
    c2_triggered = False

    values = {
        "heart_rate_bpm": heart_rate_bpm,
        "systolic_mmhg": systolic_mmhg,
        "diastolic_mmhg": diastolic_mmhg,
        "spo2_pct": spo2_pct,
    }

    def add_rule(code: str, label: str, category: str, weight: int = 0) -> None:
        rules.append(
            {"code": code, "label": label, "category": category, "weight": weight}
        )

    # --- Banderas rojas por signos vitales ---
    if spo2_pct is not None:
        if spo2_pct < 85:
            add_rule("spo2_critica", f"SpO2 {spo2_pct}% (<85%)", "C1")
            c1_triggered = True
        elif spo2_pct < 90:
            add_rule("spo2_baja", f"SpO2 {spo2_pct}% (85-89%)", "C2")
            c2_triggered = True

    if heart_rate_bpm is not None and (heart_rate_bpm < 40 or heart_rate_bpm > 150):
        add_rule("fc_critica", f"FC {heart_rate_bpm} lpm fuera de rango crítico", "C2")
        c2_triggered = True

    if systolic_mmhg is not None:
        if systolic_mmhg < 80:
            add_rule("hipotension_severa", f"PAS {systolic_mmhg} mmHg (<80)", "C2")
            c2_triggered = True
        elif systolic_mmhg >= 180:
            add_rule("crisis_hipertensiva", f"PAS {systolic_mmhg} mmHg (≥180)", "C2")
            c2_triggered = True

    if diastolic_mmhg is not None and diastolic_mmhg >= 120:
        add_rule("crisis_diastolica", f"PAD {diastolic_mmhg} mmHg (≥120)", "C2")
        c2_triggered = True

    # --- Banderas rojas por síntomas ---
    for symptom in symptoms:
        if symptom in C1_SYMPTOMS:
            add_rule(f"sintoma_{symptom}", symptom, "C1")
            c1_triggered = True
        elif symptom in C2_SYMPTOMS:
            add_rule(f"sintoma_{symptom}", symptom, "C2")
            c2_triggered = True

    if "Dolor torácico" in symptoms and (
        (spo2_pct is not None and spo2_pct < 90)
        or (systolic_mmhg is not None and systolic_mmhg < 90)
        or (heart_rate_bpm is not None and heart_rate_bpm > 120)
    ):
        add_rule("dolor_toracico_inestable", "Dolor torácico con signos de inestabilidad", "C1")
        c1_triggered = True

    if pain_scale is not None and pain_scale >= 8:
        add_rule("dolor_severo", f"Dolor {pain_scale}/10 (≥8)", "C2")
        c2_triggered = True

    # --- Severidad de cada signo vital y puntaje ---
    score = 0.0
    worst_severity = "normal"
    order = {"normal": 0, "leve": 1, "moderado": 2, "critico": 3}
    missing: list[str] = []

    for metric, value in values.items():
        label, unit = METRIC_LABELS[metric]
        if value is None:
            missing.append(label)
            continue
        band = ranges.get(metric)
        if band is None:
            missing.append(label)
            continue
        severity = classify_value(float(value), band)
        score += SEVERITY_POINTS[severity]
        if order[severity] > order[worst_severity]:
            worst_severity = severity
        if severity != "normal":
            add_rule(
                f"{metric}_{severity}",
                f"{label} {value} {unit} ({severity})",
                SEVERITY_BASE[severity],
                SEVERITY_POINTS[severity],
            )
            rationale.append(f"{label} {value} {unit}: {severity}")

    moderate_symptoms = [s for s in symptoms if s in MODERATE_SYMPTOMS]
    if moderate_symptoms:
        points = min(len(moderate_symptoms), 2)
        score += points
        for symptom in moderate_symptoms:
            add_rule(f"sintoma_{symptom}", symptom, "C4", 1)
        rationale.append("Síntomas moderados: " + ", ".join(moderate_symptoms))

    if pain_scale is not None and 5 <= pain_scale < 8:
        score += 2
        add_rule("dolor_moderado", f"Dolor {pain_scale}/10 (5-7)", "C4", 2)
        rationale.append(f"Dolor {pain_scale}/10: moderado")

    if age is not None and age >= 65:
        score += 1
        add_rule("edad_riesgo", f"Edad {age} años (≥65)", "C4", 1)
        rationale.append(f"Edad {age} años: factor de riesgo")

    if comorbidities:
        points = min(len(comorbidities), 2)
        score += points
        add_rule("comorbilidades", f"{len(comorbidities)} comorbilidad(es)", "C4", points)
        rationale.append("Comorbilidades: " + ", ".join(comorbidities))

    # --- Categoría final ---
    if c1_triggered:
        category = "C1"
    elif c2_triggered:
        category = "C2"
    else:
        base = SEVERITY_BASE[worst_severity]
        if score >= 5:
            score_category = "C3"
        elif score >= 3:
            score_category = "C4"
        else:
            score_category = "C5"
        category = min([base, score_category], key=lambda c: PRIORITY[c])
        if missing:
            add_rule("datos_incompletos", "Faltan signos vitales: " + ", ".join(missing), "C3")
            category = min([category, "C3"], key=lambda c: PRIORITY[c])
            rationale.append("Datos incompletos: se aplica mínimo C3")

    ranges_version = next(iter(ranges.values())).version if ranges else "v1"

    if c1_triggered or c2_triggered:
        rationale.insert(
            0,
            "Se activaron banderas rojas de emergencia; la categoría se asigna de forma "
            "inmediata y debe ser confirmada por un profesional.",
        )
    else:
        rationale.insert(
            0,
            f"Sin banderas rojas. Puntaje de gravedad {score:.0f}. "
            "La categoría es orientativa y debe ser confirmada por un profesional.",
        )

    return TriageResult(
        category=category,
        color=COLORS[category],
        score=score,
        triggered_rules=rules,
        rationale=" ".join(rationale),
        ranges_version=ranges_version,
    )
