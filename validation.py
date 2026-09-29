"""
validation.py — Planning Constraint Checker
============================================
Checks each proposal against configurable zoning / planning constraints.
Returns PASS / WARNING / FAIL for each constraint.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConstraintResult:
    name: str
    value: float | str
    limit: float | str
    status: str        # "PASS" | "WARNING" | "FAIL"
    message: str


def validate_proposal(metrics: dict, config: dict) -> list[ConstraintResult]:
    """
    Run all planning constraint checks against a metrics dict.

    Parameters
    ----------
    metrics : dict   — output of metrics.compute_metrics()
    config  : dict   — loaded config.yaml

    Returns
    -------
    List of ConstraintResult objects.
    """
    zoning = config.get("zoning", {})
    results: list[ConstraintResult] = []

    # ── Site area ─────────────────────────────────────────────────────────────
    site_area = float(metrics.get("site_area", 0))
    min_area = float(zoning.get("min_site_area_sqm", 10_000))
    if site_area >= min_area:
        results.append(ConstraintResult(
            "Site Area", f"{site_area:,.0f} m²", f"≥ {min_area:,.0f} m²",
            "PASS", "Site meets minimum area requirement."
        ))
    else:
        results.append(ConstraintResult(
            "Site Area", f"{site_area:,.0f} m²", f"≥ {min_area:,.0f} m²",
            "FAIL", f"Site area {site_area:,.0f} m² is below the minimum {min_area:,.0f} m²."
        ))

    # ── FAR ───────────────────────────────────────────────────────────────────
    far = float(metrics.get("far", 0))
    max_far = float(zoning.get("max_far", 4.0))
    if far <= max_far:
        results.append(ConstraintResult(
            "FAR", f"{far:.2f}", f"≤ {max_far:.2f}",
            "PASS", "Floor Area Ratio within permitted limit."
        ))
    elif far <= max_far * 1.05:
        results.append(ConstraintResult(
            "FAR", f"{far:.2f}", f"≤ {max_far:.2f}",
            "WARNING", f"FAR {far:.2f} slightly exceeds limit {max_far:.2f} (within 5%)."
        ))
    else:
        results.append(ConstraintResult(
            "FAR", f"{far:.2f}", f"≤ {max_far:.2f}",
            "FAIL", f"FAR {far:.2f} exceeds permitted maximum of {max_far:.2f}."
        ))

    # ── Building height ───────────────────────────────────────────────────────
    height = float(metrics.get("avg_building_height", 0))
    max_h = float(zoning.get("max_building_height", 100))
    if height <= max_h:
        results.append(ConstraintResult(
            "Avg Building Height", f"{height:.1f} m", f"≤ {max_h:.0f} m",
            "PASS", "Building heights within permitted limit."
        ))
    else:
        results.append(ConstraintResult(
            "Avg Building Height", f"{height:.1f} m", f"≤ {max_h:.0f} m",
            "FAIL", f"Average height {height:.1f} m exceeds maximum {max_h:.0f} m."
        ))

    # ── Green space ───────────────────────────────────────────────────────────
    green = float(metrics.get("green_percentage", 0))
    min_green = float(zoning.get("min_green_percent", 20))
    if green >= min_green:
        results.append(ConstraintResult(
            "Green Space", f"{green:.1f}%", f"≥ {min_green:.0f}%",
            "PASS", "Green space meets minimum requirement."
        ))
    elif green >= min_green * 0.85:
        results.append(ConstraintResult(
            "Green Space", f"{green:.1f}%", f"≥ {min_green:.0f}%",
            "WARNING", f"Green space {green:.1f}% is slightly below minimum {min_green:.0f}% (within 15%)."
        ))
    else:
        results.append(ConstraintResult(
            "Green Space", f"{green:.1f}%", f"≥ {min_green:.0f}%",
            "FAIL", f"Green space {green:.1f}% is well below minimum {min_green:.0f}%."
        ))

    # ── Ground coverage ───────────────────────────────────────────────────────
    cov = float(metrics.get("ground_coverage", 0))
    if cov <= 60:
        results.append(ConstraintResult(
            "Ground Coverage", f"{cov:.1f}%", "≤ 60%",
            "PASS", "Ground coverage within typical limits."
        ))
    elif cov <= 70:
        results.append(ConstraintResult(
            "Ground Coverage", f"{cov:.1f}%", "≤ 60%",
            "WARNING", f"Ground coverage {cov:.1f}% is elevated (60–70%)."
        ))
    else:
        results.append(ConstraintResult(
            "Ground Coverage", f"{cov:.1f}%", "≤ 60%",
            "FAIL", f"Ground coverage {cov:.1f}% exceeds recommended 60%."
        ))

    # ── Road presence ─────────────────────────────────────────────────────────
    roads = float(metrics.get("road_length", 0))
    if roads > 0:
        results.append(ConstraintResult(
            "Road Network", f"{roads:,.0f} m", "> 0 m",
            "PASS", "Road network present."
        ))
    else:
        results.append(ConstraintResult(
            "Road Network", "0 m", "> 0 m",
            "WARNING", "No road length recorded — verify proposal data."
        ))

    return results


def status_badge(status: str) -> str:
    """Return an emoji badge for a constraint status."""
    return {"PASS": "✅", "WARNING": "⚠️", "FAIL": "❌"}.get(status, "❓")
