"""tests/test_validation.py"""
import pytest
from validation import validate_proposal, status_badge


@pytest.fixture
def cfg():
    return {
        "zoning": {
            "max_far": 4.0,
            "max_building_height": 100,
            "min_green_percent": 20,
            "min_site_area_sqm": 10_000,
        }
    }


def _metrics(**kwargs):
    base = {
        "site_area": 100_000,
        "far": 2.0,
        "avg_building_height": 40,
        "green_percentage": 25,
        "ground_coverage": 35,
        "road_length": 2000,
    }
    base.update(kwargs)
    return base


def test_all_pass(cfg):
    results = validate_proposal(_metrics(), cfg)
    statuses = {r.name: r.status for r in results}
    assert statuses["FAR"] == "PASS"
    assert statuses["Green Space"] == "PASS"
    assert statuses["Site Area"] == "PASS"


def test_far_fail(cfg):
    results = validate_proposal(_metrics(far=5.0), cfg)
    far_r = next(r for r in results if r.name == "FAR")
    assert far_r.status == "FAIL"


def test_far_warning(cfg):
    # 4.1 is within 5% of limit 4.0
    results = validate_proposal(_metrics(far=4.1), cfg)
    far_r = next(r for r in results if r.name == "FAR")
    assert far_r.status == "WARNING"


def test_green_warning(cfg):
    # 18% is within 15% of 20%
    results = validate_proposal(_metrics(green_percentage=18), cfg)
    green_r = next(r for r in results if r.name == "Green Space")
    assert green_r.status == "WARNING"


def test_green_fail(cfg):
    results = validate_proposal(_metrics(green_percentage=10), cfg)
    green_r = next(r for r in results if r.name == "Green Space")
    assert green_r.status == "FAIL"


def test_site_area_fail(cfg):
    results = validate_proposal(_metrics(site_area=5_000), cfg)
    area_r = next(r for r in results if r.name == "Site Area")
    assert area_r.status == "FAIL"


def test_status_badge():
    assert status_badge("PASS") == "✅"
    assert status_badge("WARNING") == "⚠️"
    assert status_badge("FAIL") == "❌"


def test_no_roads_warning(cfg):
    results = validate_proposal(_metrics(road_length=0), cfg)
    road_r = next(r for r in results if r.name == "Road Network")
    assert road_r.status == "WARNING"
