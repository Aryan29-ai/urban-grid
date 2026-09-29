# UrbanGrid – Data Driven Smart City Planning
## Smart India Hackathon 2026 | PS 26114

> **"Forma designs the city. UrbanGrid explains the performance trade-offs. Revit develops the selected building."**

---

## 1. Problem Statement
PS 26114: Smart City Site Planning using Autodesk Forma Site Design.  
Design and evaluate alternative urban layouts for a site in Guntur, Andhra Pradesh, using data-driven environmental and sustainability scoring.

## 2. Project Objective
UrbanGrid is a Python/Streamlit decision-support layer that:
- Imports proposal and environmental metric data produced by **Autodesk Forma**
- Normalises, weights, and compares proposals across sustainability, daylight/solar, livability, and efficiency
- Generates a deterministic, explainable recommendation
- Produces a structured handoff package for detailed BIM development in **Autodesk Revit**

## 3. Roles

| Tool | Role |
|---|---|
| **Autodesk Forma** | Official site design and environmental simulation (wind, solar, daylight, noise) |
| **UrbanGrid (Python)** | KPI normalisation, weighted scoring, constraint checking, trade-off analysis, what-if optimisation, recommendation |
| **Autodesk Revit** | Detailed BIM development, MEP coordination, documentation |

## 4. Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 5. How to Run
```bash
streamlit run app.py
```

## 6. Input Modes

### Mode A — Forma Results / Manual Input
Upload JSON or CSV files representing data exported from Autodesk Forma.

**Expected JSON schema:**
```json
{
  "proposal_name": "Proposal A",
  "site_area": 1000000,
  "building_count": 24,
  "building_footprint_area": 180000,
  "gfa": 1440000,
  "far": 1.44,
  "ground_coverage": 18.0,
  "green_percentage": 35.0,
  "road_length": 4200,
  "road_density": 42,
  "avg_building_height": 70,
  "avg_floors": 20,
  "population_capacity": 41143,
  "carbon": 720000000,
  "sun_hours": 2200,
  "daylight": 72,
  "solar_energy": 198000,
  "wind": 68,
  "microclimate": 65,
  "noise": 55,
  "walking_distance": 85
}
```

Missing fields will be estimated using `config.yaml` assumptions (labelled "Estimated – MVP Proxy").

### Mode B — Demo Dataset
Uses pre-built synthetic data for offline demonstration. Labelled **"Demo / Estimated Data"**.  
⚠️ Demo geometry is **PYTHON DEMO DATA – NOT AN OFFICIAL FORMA SITE MODEL**.

## 7. Scoring Methodology
1. Each metric is normalised to 0–100 relative to Proposal A vs B values.
2. Negative metrics (carbon, noise, walking distance) are inverted — lower raw value → higher score.
3. Metrics are grouped into four categories.
4. Category scores are combined using configurable weights.
5. The recommendation is generated deterministically from the actual score differences.

**Default weights:** Sustainability 30% | Daylight & Solar 25% | Livability 25% | Efficiency 20%

## 8. Estimated Metric Formulas

| Metric | Formula / Source |
|---|---|
| GFA | Σ(footprint × floors) |
| FAR | GFA / site_area |
| Carbon | GFA × 500 kgCO₂e/m² (config) |
| Solar energy | roof_area × 0.5 × 5.5 kWh/m²/day × 365 × 0.20 |
| Daylight score | max(0, 100 − FAR×10 − height×0.3) |
| Wind score | max(0, 100 − coverage − FAR×5) |
| Noise score | 100 − road_density×1.2 + green_pct×0.5 |
| Walking distance | max(10, 200 − green_pct×3) |

All estimated metrics are labelled "Estimated – MVP Proxy" in the UI.

## 9. Constraint Validation
Each proposal is checked against:
- Minimum site area (1 ha)
- Maximum FAR (4.0)
- Maximum building height (100 m)
- Minimum green space (20%)
- Ground coverage (≤ 60%)
- Road network presence

Results: ✅ PASS | ⚠️ WARNING | ❌ FAIL

## 10. What-If Optimization
The sidebar provides sliders to modify Green Space %, Height, Coverage, and Road Density for Proposal A.  
The app immediately recalculates and shows the score change.  
Labelled: **"Scenario estimate – not a Forma simulation."**

## 11. Forma Board Relationship
The official comparison of site design alternatives is performed in **Autodesk Forma Board**.  
UrbanGrid adds a computational scoring/decision-support layer on top of Forma's output.

## 12. Revit Handoff
Download "Revit Handoff ZIP" containing:
- `buildings.csv` — building_id, x, y, footprint_area, height, floors, use, gfa
- `roads.csv`, `green_areas.csv`
- `site.geojson`
- `proposal_metrics.csv`
- `proposal_summary.json`
- `README.txt`

**This does NOT auto-generate an RVT file.**  
Use this structured data to set up a Revit project.

## 13. Limitations / Assumptions
- All Python metrics are geometric proxies, not professional environmental simulations.
- Shadow, wind, and noise estimates are simplified ratios — not CFD or ray-tracing.
- Population capacity assumes 35 m² GFA per person (configurable).
- Carbon estimate is GFA-based, not a lifecycle assessment.

## 14. Future Improvements
- Live Autodesk Platform Services / Forma API integration
- Real pvlib irradiance simulation (hourly)
- Wind CFD proxy via building form analysis
- Multi-scenario optimisation (not just A vs B)
- Direct Revit API parametric model generation

## 15. Running Tests
```bash
pytest
```
