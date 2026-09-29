"""tests/test_scoring.py"""
import pytest
from scoring import _normalise, calculate_scores, INVERT_METRICS


def test_metric_normalization_basic():
    assert _normalise(50, 0, 100) == pytest.approx(50.0)
    assert _normalise(0, 0, 100) == pytest.approx(0.0)
    assert _normalise(100, 0, 100) == pytest.approx(100.0)


def test_metric_normalization_inverted():
    # Best (low) value → high score when inverted
    assert _normalise(0, 0, 100, invert=True) == pytest.approx(100.0)
    assert _normalise(100, 0, 100, invert=True) == pytest.approx(0.0)
    assert _normalise(50, 0, 100, invert=True) == pytest.approx(50.0)


def test_zero_range_normalization():
    # Equal min and max → return 50
    assert _normalise(42, 42, 42) == pytest.approx(50.0)
    assert _normalise(42, 42, 42, invert=True) == pytest.approx(50.0)


def test_clamping():
    # Values outside range must be clamped to [0,100]
    assert _normalise(200, 0, 100) == pytest.approx(100.0)
    assert _normalise(-50, 0, 100) == pytest.approx(0.0)


def _make_weights(sus=30, day=25, liv=25, eff=20):
    return {"sustainability": sus, "daylight_solar": day, "livability": liv, "efficiency": eff}


def test_weighted_score_winner():
    """Proposal with better metrics should win."""
    ma = {"gfa": 100_000, "far": 2.0, "green_percentage": 40.0, "carbon": 50_000_000,
          "daylight": 80, "solar_energy": 200_000, "sun_hours": 2400,
          "noise": 70, "walking_distance": 80, "wind": 75, "microclimate": 72,
          "ground_coverage": 25, "population_capacity": 3000,
          "site_area": 100_000, "_sources": {}}
    mb = {"gfa": 100_000, "far": 2.0, "green_percentage": 15.0, "carbon": 80_000_000,
          "daylight": 55, "solar_energy": 150_000, "sun_hours": 2100,
          "noise": 35, "walking_distance": 150, "wind": 50, "microclimate": 48,
          "ground_coverage": 55, "population_capacity": 3000,
          "site_area": 100_000, "_sources": {}}
    scores = calculate_scores(ma, mb, _make_weights())
    assert scores["total_a"] > scores["total_b"]
    assert scores["winner"] == "Proposal A"


def test_weight_validation_auto_normalises():
    """Non-100 weights are auto-normalised inside calculate_scores."""
    ma = {"gfa": 50_000, "far": 1.0, "green_percentage": 30.0, "carbon": 25_000_000,
          "daylight": 70, "solar_energy": 100_000, "sun_hours": 2300,
          "noise": 60, "walking_distance": 90, "wind": 65, "microclimate": 60,
          "ground_coverage": 20, "population_capacity": 1500,
          "site_area": 50_000, "_sources": {}}
    mb = ma.copy()
    # equal proposals, any weights → scores should be very close
    scores = calculate_scores(ma, mb, {"sustainability": 50, "daylight_solar": 50, "livability": 0, "efficiency": 0})
    assert abs(scores["total_a"] - scores["total_b"]) < 5.0


def test_invert_metrics_set():
    """Known negative metrics must be in INVERT_METRICS."""
    for m in ("carbon", "noise", "walking_distance"):
        assert m in INVERT_METRICS, f"{m} should be inverted"
