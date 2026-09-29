"""
generator.py — DEMO DATA ONLY
==============================
This module generates synthetic proposal datasets SOLELY for offline
demonstration of the UrbanGrid scoring engine.

⚠️  PYTHON DEMO DATA – NOT AN OFFICIAL FORMA SITE MODEL ⚠️

In the real workflow, Proposals A and B are created in Autodesk Forma
Site Design, environmental analyses are run in Forma, and the results
are then imported into UrbanGrid for comparison and scoring.
"""

from __future__ import annotations

import math
import uuid

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.affinity import scale
from shapely.geometry import box


# ── Schema definition ─────────────────────────────────────────────────────────

PROPOSAL_SCHEMA: dict[str, str] = {
    "proposal_name": "str",
    "site_area": "float (m²)",
    "building_count": "int",
    "building_footprint_area": "float (m²)",
    "gfa": "float (m²)",
    "far": "float",
    "ground_coverage": "float (%)",
    "green_percentage": "float (%)",
    "road_length": "float (m)",
    "road_density": "float (m/ha)",
    "avg_building_height": "float (m)",
    "avg_floors": "float",
    "population_capacity": "int",
    "carbon": "float (kgCO2e)",
    "sun_hours": "float (hr/yr)",
    "daylight": "float (score 0–100)",
    "solar_energy": "float (kWh/yr)",
    "wind": "float (score 0–100)",
    "microclimate": "float (score 0–100)",
    "noise": "float (score 0–100, lower = more noise)",
    "walking_distance": "float (m)",
}


# ── Geometry generator (used for map display only) ────────────────────────────

def _make_geometry(
    site_polygon,
    block_size: float,
    road_width: float,
    building_height: float,
    coverage_ratio: float,
    crs,
) -> gpd.GeoDataFrame:
    """Return a GeoDataFrame with building / road / green geometries."""
    floor_height = 3.5
    floors = max(1, int(building_height // floor_height))

    minx, miny, maxx, maxy = site_polygon.bounds
    geometries, types, heights, floor_counts, fp_areas, gfas, bldg_ids = (
        [] for _ in range(7)
    )

    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            cell = box(x, y, x + block_size, y + block_size)
            cell_clipped = cell.intersection(site_polygon)
            if not cell_clipped.is_empty and cell_clipped.area > 50:
                block = cell_clipped.buffer(-road_width / 2.0)
                road_geom = cell_clipped.difference(block)
                if road_geom and not road_geom.is_empty:
                    geometries.append(road_geom)
                    types.append("road")
                    heights.append(0.0)
                    floor_counts.append(0)
                    fp_areas.append(0.0)
                    gfas.append(0.0)
                    bldg_ids.append("")
                if block and not block.is_empty and block.area > 50:
                    sf = math.sqrt(max(0.05, min(0.95, coverage_ratio)))
                    bldg = scale(block, xfact=sf, yfact=sf)
                    if bldg and not bldg.is_empty:
                        bfp = bldg.area
                        geometries.append(bldg)
                        types.append("building")
                        heights.append(building_height)
                        floor_counts.append(floors)
                        fp_areas.append(bfp)
                        gfas.append(bfp * floors)
                        bldg_ids.append(str(uuid.uuid4())[:8])
                    green = block.difference(bldg)
                    if green and not green.is_empty:
                        geometries.append(green)
                        types.append("green_space")
                        heights.append(0.0)
                        floor_counts.append(0)
                        fp_areas.append(0.0)
                        gfas.append(0.0)
                        bldg_ids.append("")
            y += block_size
        x += block_size

    return gpd.GeoDataFrame(
        {
            "type": types,
            "building_id": bldg_ids,
            "footprint_area": fp_areas,
            "height": heights,
            "floors": floor_counts,
            "use": ["residential" if t == "building" else t for t in types],
            "gfa": gfas,
        },
        geometry=geometries,
        crs=crs,
    )


# ── Tabular demo datasets ─────────────────────────────────────────────────────

DEMO_PROPOSAL_A: dict = {
    "proposal_name": "Proposal A – Compact High-Rise (Demo)",
    "site_area": 1_000_000,
    "building_count": 24,
    "building_footprint_area": 180_000,
    "gfa": 1_440_000,
    "far": 1.44,
    "ground_coverage": 18.0,
    "green_percentage": 35.0,
    "road_length": 4200,
    "road_density": 42,
    "avg_building_height": 70,
    "avg_floors": 20,
    "population_capacity": 41_143,
    # Environmental (estimated proxies — not Forma simulation)
    "carbon": 720_000_000,
    "sun_hours": 2200,
    "daylight": 72,
    "solar_energy": 198_000,
    "wind": 68,
    "microclimate": 65,
    "noise": 55,
    "walking_distance": 85,
    "_source": "Demo / Estimated Data",
}

DEMO_PROPOSAL_B: dict = {
    "proposal_name": "Proposal B – Spread Mid-Rise (Demo)",
    "site_area": 1_000_000,
    "building_count": 60,
    "building_footprint_area": 330_000,
    "gfa": 990_000,
    "far": 0.99,
    "ground_coverage": 33.0,
    "green_percentage": 22.0,
    "road_length": 7800,
    "road_density": 78,
    "avg_building_height": 18,
    "avg_floors": 5,
    "population_capacity": 28_286,
    # Environmental
    "carbon": 495_000_000,
    "sun_hours": 2550,
    "daylight": 86,
    "solar_energy": 181_500,
    "wind": 82,
    "microclimate": 79,
    "noise": 38,
    "walking_distance": 55,
    "_source": "Demo / Estimated Data",
}


def get_demo_geometry(site_polygon, crs, proposal: str = "A") -> gpd.GeoDataFrame:
    """Return synthetic map geometry for demo mode (for Plotly display only)."""
    if proposal == "A":
        params = dict(block_size=150, road_width=20, building_height=70, coverage_ratio=0.25)
    else:
        params = dict(block_size=80, road_width=12, building_height=18, coverage_ratio=0.55)
    return _make_geometry(site_polygon, crs=crs, **params)
