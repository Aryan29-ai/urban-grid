"""tests/test_metrics.py"""
import pytest
from metrics import compute_metrics, _safe, ESTIMATED_LABEL


@pytest.fixture
def cfg():
    return {
        "site": {"latitude": 16.3, "longitude": 80.4, "timezone": "Asia/Kolkata"},
        "solar": {"panel_efficiency": 0.20, "usable_roof_fraction": 0.5, "avg_daily_irradiance_kwh_m2": 5.5},
        "carbon": {"embodied_kgco2e_per_m2": 500, "operational_kwh_per_m2_yr": 100},
        "population": {"residential_area_per_person": 35},
        "zoning": {"max_far": 4.0, "max_building_height": 100, "min_green_percent": 20},
    }


def test_far_calculation(cfg):
    p = {"site_area": 10_000, "gfa": 30_000, "far": 3.0}
    m = compute_metrics(p, cfg)
    assert m["far"] == pytest.approx(3.0, abs=0.01)


def test_far_derived_when_missing(cfg):
    p = {"site_area": 10_000, "gfa": 20_000}   # no far field
    m = compute_metrics(p, cfg)
    assert m["far"] == pytest.approx(2.0, abs=0.01)


def test_green_percentage(cfg):
    p = {"site_area": 100_000, "gfa": 200_000, "far": 2.0, "green_percentage": 28.5}
    m = compute_metrics(p, cfg)
    assert m["green_percentage"] == pytest.approx(28.5, abs=0.01)


def test_population_capacity(cfg):
    p = {"site_area": 50_000, "gfa": 70_000, "far": 1.4}
    m = compute_metrics(p, cfg)
    # 70000 / 35 = 2000
    assert m["population_capacity"] == 2000


def test_population_passthrough(cfg):
    p = {"site_area": 50_000, "gfa": 70_000, "population_capacity": 5000}
    m = compute_metrics(p, cfg)
    assert m["population_capacity"] == 5000
    assert "population_capacity" not in m["_sources"]


def test_carbon_estimated_when_missing(cfg):
    p = {"site_area": 10_000, "gfa": 5_000}
    m = compute_metrics(p, cfg)
    assert m["carbon"] == pytest.approx(5_000 * 500, rel=0.01)
    assert m["_sources"]["carbon"] == ESTIMATED_LABEL


def test_carbon_passthrough(cfg):
    p = {"site_area": 10_000, "gfa": 5_000, "carbon": 999_999}
    m = compute_metrics(p, cfg)
    assert m["carbon"] == pytest.approx(999_999)
    assert "carbon" not in m["_sources"]


def test_safe_handles_nan():
    import math
    assert _safe(float("nan")) == 0.0
    assert _safe(float("inf")) == 0.0
    assert _safe(None) == 0.0
    assert _safe(42) == pytest.approx(42.0)
