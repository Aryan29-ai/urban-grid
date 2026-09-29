"""
scoring.py — KPI Normalization & Weighted Scoring
==================================================
Normalises all metrics to 0–100 and produces:
  - per-metric normalised scores
  - category scores (sustainability / daylight_solar / livability / efficiency)
  - overall weighted score
  - deterministic plain-English recommendation
"""

from __future__ import annotations

import numpy as np


# Metrics that should be inverted (lower raw value = better score)
INVERT_METRICS = {
    "carbon",
    "noise",           # raw noise score = noise level, lower is better
    "walking_distance",
    "net_operational_energy",
    "ground_coverage",
}

# Category → constituent metric keys
CATEGORY_METRICS: dict[str, list[str]] = {
    "sustainability": ["carbon", "green_percentage"],
    "daylight_solar": ["daylight", "solar_energy", "sun_hours"],
    "livability": ["noise", "walking_distance", "wind", "microclimate"],
    "efficiency": ["far", "ground_coverage", "population_capacity"],
}


def _normalise(val: float, lo: float, hi: float, invert: bool = False) -> float:
    """Map val ∈ [lo, hi] → [0, 100].  Returns 50 if lo == hi."""
    if hi == lo:
        return 50.0
    score = (val - lo) / (hi - lo) * 100.0
    score = max(0.0, min(100.0, score))
    return 100.0 - score if invert else score


def _category_score(norm_scores: dict[str, float], keys: list[str]) -> float:
    vals = [norm_scores[k] for k in keys if k in norm_scores]
    return float(np.mean(vals)) if vals else 50.0


def calculate_scores(
    metrics_a: dict,
    metrics_b: dict,
    weights: dict[str, float],
) -> dict:
    """
    Calculate normalised scores, category scores, and overall scores.

    Parameters
    ----------
    metrics_a / metrics_b : output of metrics.compute_metrics()
    weights : dict with keys sustainability, daylight_solar, livability, efficiency
              (values should sum to 100)

    Returns
    -------
    Large dict with all score data + recommendation text.
    """
    # Collect all numeric metric keys present in both proposals
    all_keys = set(metrics_a) | set(metrics_b)
    numeric_keys = [
        k for k in all_keys
        if not k.startswith("_") and k != "proposal_name"
        and isinstance(metrics_a.get(k, metrics_b.get(k)), (int, float, np.integer, np.floating))
    ]

    # Normalise each metric relative to A vs B range (wider bounds for stability)
    norm_a: dict[str, float] = {}
    norm_b: dict[str, float] = {}
    contributions: dict[str, dict[str, float]] = {"A": {}, "B": {}}

    for k in numeric_keys:
        va = float(metrics_a.get(k, 0) or 0)
        vb = float(metrics_b.get(k, 0) or 0)
        lo = min(va, vb) * 0.8
        hi = max(va, vb) * 1.2
        invert = k in INVERT_METRICS
        norm_a[k] = _normalise(va, lo, hi, invert)
        norm_b[k] = _normalise(vb, lo, hi, invert)

    # Category scores
    cat_a = {c: _category_score(norm_a, keys) for c, keys in CATEGORY_METRICS.items()}
    cat_b = {c: _category_score(norm_b, keys) for c, keys in CATEGORY_METRICS.items()}

    # Overall score — weight-normalised
    w_sum = sum(weights.values()) or 100
    total_a = sum(cat_a[c] * weights.get(c, 0) / w_sum for c in CATEGORY_METRICS)
    total_b = sum(cat_b[c] * weights.get(c, 0) / w_sum for c in CATEGORY_METRICS)

    winner = "Proposal A" if total_a >= total_b else "Proposal B"
    loser  = "Proposal B" if winner == "Proposal A" else "Proposal A"
    w_score = max(total_a, total_b)
    l_score = min(total_a, total_b)
    diff = w_score - l_score

    # Top 3 metrics driving the difference
    metric_diffs: dict[str, float] = {}
    for k in numeric_keys:
        if k in {"site_area", "building_count", "avg_floors"}:
            continue
        sa = norm_a.get(k, 50)
        sb = norm_b.get(k, 50)
        metric_diffs[k] = (sa - sb) if winner == "Proposal A" else (sb - sa)

    top3 = sorted(metric_diffs.items(), key=lambda x: x[1], reverse=True)[:3]
    bot3 = sorted(metric_diffs.items(), key=lambda x: x[1])[:3]

    def fmt(k: str) -> str:
        return k.replace("_", " ").title()

    top3_names = [fmt(k) for k, _ in top3 if _ > 0.1][:3]
    bot3_names = [fmt(k) for k, _ in bot3 if _ < -0.1][:3]

    if not top3_names:
        top3_names = ["Overall balance"]

    recommendation = (
        f"**{winner}** has an estimated UrbanGrid score of **{w_score:.1f}** "
        f"compared with **{l_score:.1f}** for {loser}, a difference of **{diff:.1f} points**.\n\n"
        f"**Top contributing improvements in {winner}:**\n"
        + "".join(f"{i+1}. {n}\n" for i, n in enumerate(top3_names))
    )
    if bot3_names:
        recommendation += (
            f"\n**Areas where {loser} performs better:**\n"
            + "".join(f"- {n}\n" for n in bot3_names)
        )

    return {
        "norm_a": norm_a,
        "norm_b": norm_b,
        "cat_a": cat_a,
        "cat_b": cat_b,
        "total_a": total_a,
        "total_b": total_b,
        "winner": winner,
        "loser": loser,
        "diff": diff,
        "top3": top3_names,
        "bot3": bot3_names,
        "recommendation": recommendation,
    }
