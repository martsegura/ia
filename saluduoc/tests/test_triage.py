"""Tests unitarios del motor de triage."""

from app.models.normal_range import NormalRange
from app.services.triage import assess


def build_ranges() -> dict[str, NormalRange]:
    return {
        "heart_rate_bpm": NormalRange(
            metric="heart_rate_bpm",
            label="FC",
            normal_min=60,
            normal_max=100,
            mild_low=60,
            moderate_low=50,
            critical_low=40,
            mild_high=120,
            critical_high=151,
            version="v1",
        ),
        "systolic_mmhg": NormalRange(
            metric="systolic_mmhg",
            label="PAS",
            normal_min=90,
            normal_max=119,
            mild_low=90,
            moderate_low=90,
            critical_low=80,
            mild_high=139,
            critical_high=180,
            version="v1",
        ),
        "diastolic_mmhg": NormalRange(
            metric="diastolic_mmhg",
            label="PAD",
            normal_min=60,
            normal_max=79,
            mild_low=60,
            moderate_low=60,
            critical_low=50,
            mild_high=89,
            critical_high=120,
            version="v1",
        ),
        "spo2_pct": NormalRange(
            metric="spo2_pct",
            label="SpO2",
            normal_min=95,
            normal_max=100,
            mild_low=95,
            moderate_low=92,
            critical_low=85,
            version="v1",
        ),
    }


def run(**overrides):
    data = {
        "heart_rate_bpm": 78,
        "systolic_mmhg": 118,
        "diastolic_mmhg": 76,
        "spo2_pct": 97,
        "symptoms": [],
        "pain_scale": 0,
        "age": 30,
        "comorbidities": [],
        "ranges": build_ranges(),
    }
    data.update(overrides)
    return assess(**data)


def test_normal_values_are_c5():
    result = run()
    assert result.category == "C5"
    assert result.color == "verde"


def test_spo2_critical_is_c1():
    result = run(spo2_pct=84)
    assert result.category == "C1"
    assert result.color == "rojo"
    assert any(rule["code"] == "spo2_critica" for rule in result.triggered_rules)


def test_spo2_low_is_c2():
    result = run(spo2_pct=87)
    assert result.category == "C2"


def test_chest_pain_is_c2():
    result = run(symptoms=["Dolor torácico"])
    assert result.category == "C2"


def test_chest_pain_with_instability_is_c1():
    result = run(symptoms=["Dolor torácico"], spo2_pct=88)
    assert result.category == "C1"


def test_hypertensive_crisis_is_c2():
    result = run(systolic_mmhg=185)
    assert result.category == "C2"


def test_severe_pain_is_c2():
    result = run(pain_scale=9)
    assert result.category == "C2"


def test_moderate_hr_and_age_is_c3():
    result = run(heart_rate_bpm=135, age=70)
    assert result.category == "C3"


def test_mild_hr_is_c4():
    result = run(heart_rate_bpm=110)
    assert result.category == "C4"


def test_missing_vitals_force_minimum_c3():
    result = run(systolic_mmhg=None, diastolic_mmhg=None, spo2_pct=None)
    assert result.category == "C3"
    assert any(rule["code"] == "datos_incompletos" for rule in result.triggered_rules)


def test_hr_boundary_40_is_moderate():
    assert run(heart_rate_bpm=40).category == "C3"


def test_hr_boundary_39_is_c2():
    assert run(heart_rate_bpm=39).category == "C2"


def test_spo2_boundary_85_is_c2():
    # 85% activa la bandera roja de hipoxemia (C2), aunque el límite crítico sea <85.
    assert run(spo2_pct=85).category == "C2"


def test_spo2_boundary_92_is_mild():
    assert run(spo2_pct=92).category == "C4"


def test_sleep_is_not_used_for_triage():
    # sleep_quality no forma parte de los signos evaluados por el motor
    result = run()
    assert result.category == "C5"
