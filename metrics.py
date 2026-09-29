"""
metrics.py — Urban Performance Metrics
=======================================
Processes proposal data and computes KPI scores.

When real Autodesk Forma values are supplied they are used directly.
When a field is missing or zero, a simplified proxy estimate is computed
and clearly labelled "Estimated – MVP Proxy".

FORMULA DOCUMENTATION
---------------------
GFA          = Σ(footprint_area × floors)
FAR          = GFA / site_area
Coverage %   = Σ(footprint_area) / site_area × 100
Green %      = green_area / site_area × 100
Population   = residential_GFA / residential_m2_per_person
Carbon       = GFA × embodied_kgCO2e_per_m2  [proxy]
Solar_kWh    = roof_area × usable_fraction × irradiance × efficiency × 365 [proxy]
Daylight     = max(0, 100 − FAR × 10 − avg_height × 0.3)  [proxy]
Wind         = max(0, 100 − ground_coverage_pct − FAR × 5)  [proxy]
Noise        = road_density × 1.2 − green_pct × 0.5  [proxy]
Walking dist = max(10, 200 − green_pct × 3)  [proxy]
"""

from __future__ import annotations

import math
import numpy as np
import pandas as pd
import pvlib


# Marker for values that were estimated rather than sourced from Forma
ESTIMATED_LABEL = "Estimated – MVP Proxy"


def _safe(val, fallback: float = 0.0) -> float:
    """Return float; return fallback for None / NaN / inf."""
    try:
        v = float(val)
        return fallback if (math.isnan(v) or math.isinf(v)) else v
    except (TypeError, ValueError):
        return fallback


def compute_metrics(proposal: dict, config: dict) -> dict[str, object]:
    """
    Build a full metrics dict from a proposal dict.

    Parameters
    ----------
    proposal : dict   — field values (from Forma import or demo data)
    config   : dict   — loaded config.yaml

    Returns
    -------
    dict with metric values + a 'sources' sub-dict indicating
    which values came from Forma vs were estimated.
    """
    cfg_solar = config.get("solar", {})
    cfg_carbon = config.get("carbon", {})
    cfg_pop = config.get("population", {})

    site_area = _safe(proposal.get("site_area", 1_000_000), 1_000_000)

    # ── Area metrics ─────────────────────────────────────────────────────────
    gfa = _safe(proposal.get("gfa"))
    far = _safe(proposal.get("far"), gfa / site_area if site_area else 0)
    coverage = _safe(proposal.get("ground_coverage"))
    green_pct = _safe(proposal.get("green_percentage"))
    road_density = _safe(proposal.get("road_density"))
    road_length = _safe(proposal.get("road_length"))
    avg_height = _safe(proposal.get("avg_building_height"))
    avg_floors = _safe(proposal.get("avg_floors"))
    building_count = _safe(proposal.get("building_count"))
    building_footprint = _safe(proposal.get("building_footprint_area"))
    pop_capacity = _safe(proposal.get("population_capacity"))

    sources: dict[str, str] = {}

    # Population — derive if zero
    if pop_capacity <= 0:
        rpp = _safe(cfg_pop.get("residential_area_per_person", 35), 35)
        pop_capacity = int(gfa / rpp) if rpp > 0 else 0
        sources["population_capacity"] = ESTIMATED_LABEL

    # ── Environmental metrics ─────────────────────────────────────────────────

    # Carbon — use supplied or estimate
    carbon = _safe(proposal.get("carbon"))
    if carbon <= 0:
        ec = _safe(cfg_carbon.get("embodied_kgco2e_per_m2", 500), 500)
        carbon = gfa * ec
        sources["carbon"] = ESTIMATED_LABEL

    # Solar energy — use supplied or estimate
    solar_energy = _safe(proposal.get("solar_energy"))
    if solar_energy <= 0:
        eff = _safe(cfg_solar.get("panel_efficiency", 0.20), 0.20)
        usable = _safe(cfg_solar.get("usable_roof_fraction", 0.5), 0.5)
        irr = _safe(cfg_solar.get("avg_daily_irradiance_kwh_m2", 5.5), 5.5)
        roof_area = building_footprint if building_footprint > 0 else site_area * (coverage / 100)
        solar_energy = roof_area * usable * irr * 365 * eff
        sources["solar_energy"] = ESTIMATED_LABEL

    # Sun hours — use supplied or rough proxy
    sun_hours = _safe(proposal.get("sun_hours"))
    if sun_hours <= 0:
        sun_hours = _estimate_sun_hours(config)
        sources["sun_hours"] = ESTIMATED_LABEL

    # Daylight score 0-100 — use supplied or proxy
    daylight = _safe(proposal.get("daylight"))
    if daylight <= 0:
        daylight = max(0.0, 100 - far * 10 - avg_height * 0.3)
        sources["daylight"] = ESTIMATED_LABEL

    # Wind score 0-100
    wind = _safe(proposal.get("wind"))
    if wind <= 0:
        wind = max(0.0, 100 - coverage - far * 5)
        sources["wind"] = ESTIMATED_LABEL

    # Microclimate score 0-100
    microclimate = _safe(proposal.get("microclimate"))
    if microclimate <= 0:
        microclimate = (wind + green_pct) / 2.0
        sources["microclimate"] = ESTIMATED_LABEL

    # Noise score 0-100 (lower = noisier)
    noise = _safe(proposal.get("noise"))
    if noise <= 0:
        noise = max(0.0, min(100.0, 100 - road_density * 1.2 + green_pct * 0.5))
        sources["noise"] = ESTIMATED_LABEL

    # Walking distance to green
    walking_distance = _safe(proposal.get("walking_distance"))
    if walking_distance <= 0:
        walking_distance = max(10.0, 200 - green_pct * 3)
        sources["walking_distance"] = ESTIMATED_LABEL

    # Net operational energy (proxy)
    op_energy = gfa * _safe(cfg_carbon.get("operational_kwh_per_m2_yr", 100), 100)
    net_energy = max(0.0, op_energy - solar_energy)
    sources["net_operational_energy"] = ESTIMATED_LABEL

    return {
        # Area
        "proposal_name": proposal.get("proposal_name", "Unknown"),
        "site_area": site_area,
        "building_count": int(building_count),
        "building_footprint_area": building_footprint,
        "gfa": gfa,
        "far": far,
        "ground_coverage": coverage,
        "green_percentage": green_pct,
        "road_length": road_length,
        "road_density": road_density,
        "avg_building_height": avg_height,
        "avg_floors": avg_floors,
        "population_capacity": int(pop_capacity),
        # Environmental
        "carbon": carbon,
        "sun_hours": sun_hours,
        "daylight": daylight,
        "solar_energy": solar_energy,
        "wind": wind,
        "microclimate": microclimate,
        "noise": noise,
        "walking_distance": walking_distance,
        "net_operational_energy": net_energy,
        # Metadata
        "_source": proposal.get("_source", "Imported"),
        "_sources": sources,
    }


def _estimate_sun_hours(config: dict) -> float:
    """Use pvlib to get a rough annual sun-hours estimate for the configured site."""
    try:
        lat = config.get("site", {}).get("latitude", 16.3)
        lon = config.get("site", {}).get("longitude", 80.4)
        tz = config.get("site", {}).get("timezone", "Asia/Kolkata")

        times = pd.date_range(
            "2026-01-01", "2026-12-31", freq="3h", tz=tz
        )
        solpos = pvlib.solarposition.get_solarposition(times, lat, lon)
        sun_hours = float((solpos["elevation"] > 5).sum() * 3)
        return sun_hours
    except Exception:
        return 2400.0
