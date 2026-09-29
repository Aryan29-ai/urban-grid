"""
app.py — UrbanGrid Streamlit Dashboard
=======================================
UrbanGrid – Data Driven Smart City Planning
Smart India Hackathon 2026 | PS 26114

Design principle:
  "Forma designs the city.
   UrbanGrid explains the performance trade-offs.
   Revit develops the selected building."
"""

from __future__ import annotations

import io
import json

import geopandas as gpd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yaml

import export as exp
import metrics as met
import scoring as sc
import validation as val
from generator import DEMO_PROPOSAL_A, DEMO_PROPOSAL_B, get_demo_geometry

# ═══════════════════════════════════════════════════════════════════════════════
# Page config
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="UrbanGrid – Smart City Planning",
    page_icon="🏙️",
    layout="wide",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .title-block {background: linear-gradient(135deg,#0f2027,#203a43,#2c5364);
    padding:2rem 2.5rem;border-radius:12px;color:#fff;margin-bottom:1.5rem;}
  .title-block h1{margin:0;font-size:2.2rem;font-weight:800;}
  .title-block p{margin:0.4rem 0 0;font-size:1rem;opacity:.85;}
  .kpi-card{background:#1e2d3d;border-radius:10px;padding:1rem 1.2rem;
    border-left:4px solid #4fc3f7;color:#fff;}
  .kpi-card .label{font-size:.8rem;opacity:.7;margin-bottom:.2rem;}
  .kpi-card .value{font-size:1.6rem;font-weight:700;}
  .section-header{font-size:1.1rem;font-weight:700;color:#4fc3f7;
    border-bottom:1px solid #2d4a6b;padding-bottom:0.4rem;margin:1.5rem 0 0.8rem;}
  .workflow-box{background:#0d1b2a;border:1px solid #2d4a6b;border-radius:8px;
    padding:1rem;font-family:monospace;font-size:.85rem;line-height:1.8;color:#b0c4de;}
  .recommendation-box{background:linear-gradient(135deg,#0a3d62,#1a5276);
    border-left:6px solid #27ae60;border-radius:12px;padding:1.5rem;color:#fff;}
  .disclaimer{background:#1a1a2e;border-left:4px solid #e67e22;
    border-radius:6px;padding:.8rem 1rem;font-size:.8rem;color:#f0a500;}
  .footer{text-align:center;color:#666;font-size:.8rem;margin-top:3rem;
    padding-top:1rem;border-top:1px solid #2d4a6b;}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_data
def load_config() -> dict:
    with open("config.yaml") as f:
        return yaml.safe_load(f)

config = load_config()
scoring_cfg = config.get("scoring", {})

# ═══════════════════════════════════════════════════════════════════════════════
# Header
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="title-block">
  <h1>🏙️ UrbanGrid – Data Driven Smart City Planning</h1>
  <p>Smart India Hackathon 2026 &nbsp;|&nbsp; PS 26114 – Smart City Site Planning using Autodesk Forma</p>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="disclaimer">⚠️ <strong>Disclaimer:</strong> UrbanGrid MVP metrics are simplified estimates/proxies for demonstration. Proposals A and B are created in Autodesk Forma Site Design. UrbanGrid is the decision-support scoring layer — not a replacement for Forma simulations.</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Autodesk_logo.svg/320px-Autodesk_logo.svg.png" if False else None, use_container_width=False)  # skip logo; offline
st.sidebar.title("UrbanGrid Controls")

# ── Mode ──────────────────────────────────────────────────────────────────────
st.sidebar.markdown("### Input Mode")
mode = st.sidebar.radio(
    "Select data source:",
    ["🧪 Demo Dataset", "📥 Forma Results / Manual Input"],
    help="Demo uses pre-built example data. Forma mode imports your exported results.",
)
demo_mode = mode.startswith("🧪")

# ── Site ──────────────────────────────────────────────────────────────────────
st.sidebar.markdown("### Site Boundary")
site_file = st.sidebar.file_uploader("Upload site GeoJSON (optional)", type=["geojson","json"])

@st.cache_data
def load_default_site() -> gpd.GeoDataFrame:
    return gpd.read_file("data/site.geojson")

def load_site(file) -> gpd.GeoDataFrame | None:
    try:
        gdf = gpd.read_file(file)
        gdf.geometry = gdf.geometry.buffer(0)
        if gdf.empty:
            st.sidebar.error("Uploaded file has empty geometry.")
            return None
        return gdf
    except Exception as e:
        st.sidebar.error(f"Could not load site: {e}")
        return None

site_gdf_raw = load_site(site_file) if site_file else load_default_site()
if site_gdf_raw is None:
    site_gdf_raw = load_default_site()

crs = config.get("site", {}).get("crs", "EPSG:32644")
site_gdf = site_gdf_raw.to_crs(crs)
site_polygon = site_gdf.geometry.iloc[0]
site_area = site_polygon.area

if site_area < 1000:
    st.error("⛔ Site area is too small. Please upload a site of at least 0.1 ha.")
    st.stop()

st.sidebar.success(f"Site: {site_area/10_000:.2f} Ha  ({site_area:,.0f} m²)")

# ── Scoring weights ────────────────────────────────────────────────────────────
st.sidebar.markdown("### Planning Priorities (Weights)")
st.sidebar.caption("Adjust to reflect your planning objectives.")

w_sus = st.sidebar.slider("Sustainability", 0, 100, int(scoring_cfg.get("sustainability", 30)), key="w_sus")
w_day = st.sidebar.slider("Daylight & Solar", 0, 100, int(scoring_cfg.get("daylight_solar", 25)), key="w_day")
w_liv = st.sidebar.slider("Livability", 0, 100, int(scoring_cfg.get("livability", 25)), key="w_liv")
w_eff = st.sidebar.slider("Efficiency", 0, 100, int(scoring_cfg.get("efficiency", 20)), key="w_eff")

w_total = w_sus + w_day + w_liv + w_eff
if w_total == 0:
    st.sidebar.error("Weights cannot all be zero.")
    st.stop()
st.sidebar.caption(f"Total weight: {w_total} {'✅' if w_total == 100 else '⚠️ (auto-normalised)'}")

weights = {
    "sustainability": w_sus,
    "daylight_solar": w_day,
    "livability": w_liv,
    "efficiency": w_eff,
}

# ── What-if sliders ────────────────────────────────────────────────────────────
st.sidebar.markdown("### What-If Scenario (applied to Proposal A)")
st.sidebar.caption("Scenario estimate – not a Forma simulation.")
wi_green   = st.sidebar.slider("Green Space %",       0,  60, 0, key="wi_green")
wi_height  = st.sidebar.slider("Avg Building Height (m)", 0, 100, 0, key="wi_height")
wi_cov     = st.sidebar.slider("Ground Coverage %",   0,  80, 0, key="wi_cov")
wi_density = st.sidebar.slider("Road Density (m/ha)", 0, 150,  0, key="wi_density")

# ═══════════════════════════════════════════════════════════════════════════════
# Load / Input proposal data
# ═══════════════════════════════════════════════════════════════════════════════

proposal_a_raw: dict = {}
proposal_b_raw: dict = {}
gdf_a: gpd.GeoDataFrame | None = None
gdf_b: gpd.GeoDataFrame | None = None

if demo_mode:
    proposal_a_raw = DEMO_PROPOSAL_A.copy()
    proposal_b_raw = DEMO_PROPOSAL_B.copy()
    with st.spinner("Generating demo geometry…"):
        gdf_a = get_demo_geometry(site_polygon, site_gdf.crs, "A")
        gdf_b = get_demo_geometry(site_polygon, site_gdf.crs, "B")
    st.info("🧪 **Demo Dataset active.** Data is pre-built for demonstration. No Forma import required.")
else:
    # ── Forma Results import ──────────────────────────────────────────────────
    st.markdown("### 📥 Import Proposal Data from Forma")
    st.markdown(
        "Upload the proposal and environmental metrics you exported from **Autodesk Forma**. "
        "Supported formats: JSON or CSV."
    )
    col_up_a, col_up_b = st.columns(2)

    def _parse_upload(file) -> dict | None:
        if file is None:
            return None
        try:
            content = file.read()
            if file.name.endswith(".json"):
                return json.loads(content)
            else:  # CSV
                df = pd.read_csv(io.StringIO(content.decode()))
                return df.iloc[0].to_dict()
        except Exception as e:
            st.error(f"Could not parse {file.name}: {e}")
            return None

    with col_up_a:
        st.markdown("**Proposal A**")
        f_a = st.file_uploader("Upload Proposal A (JSON/CSV)", type=["json","csv"], key="fa")
        parsed_a = _parse_upload(f_a)
        if parsed_a:
            proposal_a_raw = parsed_a
            st.success(f"✅ Proposal A loaded: {parsed_a.get('proposal_name','')}")
        else:
            st.warning("No Proposal A data yet — showing placeholder.")
            proposal_a_raw = {"proposal_name": "Proposal A (awaiting Forma data)", "site_area": site_area}

    with col_up_b:
        st.markdown("**Proposal B**")
        f_b = st.file_uploader("Upload Proposal B (JSON/CSV)", type=["json","csv"], key="fb")
        parsed_b = _parse_upload(f_b)
        if parsed_b:
            proposal_b_raw = parsed_b
            st.success(f"✅ Proposal B loaded: {parsed_b.get('proposal_name','')}")
        else:
            st.warning("No Proposal B data yet — showing placeholder.")
            proposal_b_raw = {"proposal_name": "Proposal B (awaiting Forma data)", "site_area": site_area}

# ═══════════════════════════════════════════════════════════════════════════════
# Compute metrics & scores
# ═══════════════════════════════════════════════════════════════════════════════
with st.spinner("Computing metrics…"):
    metrics_a = met.compute_metrics(proposal_a_raw, config)
    metrics_b = met.compute_metrics(proposal_b_raw, config)
    scores = sc.calculate_scores(metrics_a, metrics_b, weights)

# What-if variant of Proposal A
metrics_a_wi = metrics_a.copy()
any_wi = wi_green or wi_height or wi_cov or wi_density
if any_wi:
    if wi_green:   metrics_a_wi["green_percentage"]   = float(wi_green)
    if wi_height:  metrics_a_wi["avg_building_height"] = float(wi_height)
    if wi_cov:     metrics_a_wi["ground_coverage"]     = float(wi_cov)
    if wi_density: metrics_a_wi["road_density"]         = float(wi_density)
    scores_wi = sc.calculate_scores(metrics_a_wi, metrics_b, weights)
else:
    scores_wi = None

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Site Overview
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📍 1. Site Overview</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
def kpi(col, label, value):
    col.markdown(f'<div class="kpi-card"><div class="label">{label}</div><div class="value">{value}</div></div>', unsafe_allow_html=True)

kpi(c1, "Site Area", f"{site_area/10_000:.2f} Ha")
kpi(c2, "Location", "Guntur, AP")
kpi(c3, "Input Mode", "Demo" if demo_mode else "Forma Import")
kpi(c4, "CRS", crs.split(":")[-1])

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Forma Comparison Workflow
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">🔄 2. Forma Comparison Workflow</div>', unsafe_allow_html=True)
st.markdown("""
<div class="workflow-box">
 Autodesk Forma Site Design<br>
 &nbsp;&nbsp;&nbsp;↓<br>
 Create Site → Create Proposal A → Create Proposal B<br>
 &nbsp;&nbsp;&nbsp;↓<br>
 Run Forma Environmental Analyses (wind, daylight, solar, noise …)<br>
 &nbsp;&nbsp;&nbsp;↓<br>
 Compare using <strong>Forma Board</strong><br>
 &nbsp;&nbsp;&nbsp;↓<br>
 Export / transfer proposal + metrics data<br>
 &nbsp;&nbsp;&nbsp;↓<br>
 <strong>UrbanGrid Python Engine</strong><br>
 &nbsp;&nbsp;&nbsp;→ KPI normalisation &nbsp;→ Weighted scoring<br>
 &nbsp;&nbsp;&nbsp;→ Constraint checking &nbsp;→ Trade-off analysis<br>
 &nbsp;&nbsp;&nbsp;→ What-if optimisation &nbsp;→ Recommendation<br>
 &nbsp;&nbsp;&nbsp;↓<br>
 Selected Proposal &nbsp;→&nbsp; <strong>Autodesk Revit</strong> BIM Development
</div>
<br>
<em style="font-size:.8rem;color:#888;">Official proposal comparison is performed in Autodesk Forma Board.
UrbanGrid adds a computational scoring and decision-support layer.</em>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Visual Maps (demo mode) or metric comparison
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">🗺️ 3. Proposal A vs Proposal B</div>', unsafe_allow_html=True)

if demo_mode and gdf_a is not None and not gdf_a.empty:
    st.caption("🧪 PYTHON DEMO DATA – NOT AN OFFICIAL FORMA SITE MODEL")

    def make_map(gdf: gpd.GeoDataFrame, title: str) -> go.Figure:
        gdf_wgs = gdf.to_crs(epsg=4326)
        color_map = {"building": "#4fc3f7", "road": "#78909c", "green_space": "#66bb6a"}
        fig = go.Figure()
        for layer_type, color in color_map.items():
            subset = gdf_wgs[gdf_wgs["type"] == layer_type]
            if subset.empty:
                continue
            hover = subset.apply(
                lambda r: f"Type: {r['type']}<br>Height: {r.get('height',0):.0f} m<br>GFA: {r.get('gfa',0):.0f} m²",
                axis=1,
            ).tolist()
            for _, row in subset.iterrows():
                geom = row.geometry
                if geom is None or geom.is_empty:
                    continue
                try:
                    xs, ys = geom.exterior.xy if hasattr(geom, "exterior") else ([], [])
                except Exception:
                    continue
                fig.add_trace(go.Scattermap(
                    lat=list(ys) + [ys[0]] if ys else [],
                    lon=list(xs) + [xs[0]] if xs else [],
                    mode="lines",
                    fill="toself",
                    fillcolor=color,
                    line=dict(color=color, width=0.5),
                    opacity=0.75,
                    hoverinfo="skip",
                    showlegend=False,
                ))
        # Legend traces
        for label, color in color_map.items():
            fig.add_trace(go.Scattermap(lat=[None], lon=[None], mode="markers",
                marker=dict(color=color, size=10),
                name=label.replace("_"," ").title(), showlegend=True))
        lat_c = gdf_wgs.geometry.centroid.y.mean()
        lon_c = gdf_wgs.geometry.centroid.x.mean()
        fig.update_layout(
            map=dict(style="carto-darkmatter", center=dict(lat=lat_c, lon=lon_c), zoom=13),
            title=title, height=420, margin=dict(l=0,r=0,t=40,b=0),
            legend=dict(orientation="h", x=0, y=-0.05),
            paper_bgcolor="#0d1b2a", plot_bgcolor="#0d1b2a", font_color="#fff",
        )
        return fig

    mc1, mc2 = st.columns(2)
    with mc1:
        st.plotly_chart(make_map(gdf_a, "Proposal A – Compact High-Rise"), use_container_width=True)
    with mc2:
        st.plotly_chart(make_map(gdf_b, "Proposal B – Spread Mid-Rise"), use_container_width=True)
else:
    # Tabular visual comparison
    st.info("Metric comparison view (upload geometry or use Demo mode for maps).")
    compare_keys = ["building_count","gfa","far","ground_coverage","green_percentage",
                    "avg_building_height","avg_floors","population_capacity","road_density"]
    df_comp = pd.DataFrame({
        "Metric": [k.replace("_"," ").title() for k in compare_keys],
        "Proposal A": [f"{metrics_a.get(k,0):,.1f}" for k in compare_keys],
        "Proposal B": [f"{metrics_b.get(k,0):,.1f}" for k in compare_keys],
    })
    st.dataframe(df_comp, use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Urban Site Summary (KPI table)
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📊 4. Urban Site Summary</div>', unsafe_allow_html=True)
summary_keys = [
    ("Site Area (m²)", "site_area"),
    ("Building Count", "building_count"),
    ("Building Footprint (m²)", "building_footprint_area"),
    ("GFA (m²)", "gfa"),
    ("FAR", "far"),
    ("Ground Coverage (%)", "ground_coverage"),
    ("Green Space (%)", "green_percentage"),
    ("Road Length (m)", "road_length"),
    ("Road Density (m/ha)", "road_density"),
    ("Avg Height (m)", "avg_building_height"),
    ("Avg Floors", "avg_floors"),
    ("Population Capacity", "population_capacity"),
]
df_summ = pd.DataFrame({
    "Metric": [label for label, _ in summary_keys],
    "Proposal A": [f"{metrics_a.get(k,0):,.1f}" for _, k in summary_keys],
    "Proposal B": [f"{metrics_b.get(k,0):,.1f}" for _, k in summary_keys],
})
st.dataframe(df_summ, use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Planning Compliance
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">✅ 5. Planning Compliance</div>', unsafe_allow_html=True)
cc1, cc2 = st.columns(2)

def render_compliance(col, mets: dict, label: str):
    results = val.validate_proposal(mets, config)
    col.markdown(f"**{label}**")
    rows = []
    for r in results:
        badge = val.status_badge(r.status)
        rows.append({"Constraint": r.name, "Value": r.value, "Limit": r.limit, "Status": f"{badge} {r.status}"})
    col.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with cc1:
    render_compliance(cc1, metrics_a, "Proposal A")
with cc2:
    render_compliance(cc2, metrics_b, "Proposal B")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Environmental Metrics
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">🌿 6. Environmental Metrics</div>', unsafe_allow_html=True)
st.caption("*Metrics marked with ⚡ are simplified estimates (MVP proxy). Forma simulation values override these when imported.*")

env_keys = [
    ("Carbon (kgCO₂e)", "carbon"),
    ("Sun Hours (hr/yr)", "sun_hours"),
    ("Daylight Score (0–100)", "daylight"),
    ("Solar Energy (kWh/yr)", "solar_energy"),
    ("Wind Score (0–100)", "wind"),
    ("Microclimate Score (0–100)", "microclimate"),
    ("Noise Score (0–100)", "noise"),
    ("Walking Distance (m)", "walking_distance"),
    ("Net Operational Energy (kWh/yr)", "net_operational_energy"),
]

def src_tag(mets, key):
    return " ⚡" if key in mets.get("_sources", {}) else ""

df_env = pd.DataFrame({
    "Metric": [label + src_tag(metrics_a, k) for label, k in env_keys],
    "Proposal A": [f"{metrics_a.get(k,0):,.1f}" for _, k in env_keys],
    "Proposal B": [f"{metrics_b.get(k,0):,.1f}" for _, k in env_keys],
})
st.dataframe(df_env, use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — Urban Performance Profile (Radar)
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📡 7. Urban Performance Profile</div>', unsafe_allow_html=True)

radar_keys = ["sustainability", "daylight_solar", "livability", "efficiency"]
radar_labels = ["Sustainability", "Daylight & Solar", "Livability", "Efficiency"]

fig_radar = go.Figure()
for name, cat_scores, color in [
    ("Proposal A", scores["cat_a"], "#4fc3f7"),
    ("Proposal B", scores["cat_b"], "#66bb6a"),
]:
    vals = [cat_scores.get(k, 50) for k in radar_keys]
    vals += vals[:1]
    fig_radar.add_trace(go.Scatterpolar(
        r=vals,
        theta=radar_labels + [radar_labels[0]],
        fill="toself",
        name=name,
        line_color=color,
        fillcolor=color,
        opacity=0.35,
    ))
fig_radar.update_layout(
    polar=dict(radialaxis=dict(visible=True, range=[0, 100], color="#888")),
    legend=dict(orientation="h", x=0.2, y=-0.1),
    paper_bgcolor="#0d1b2a", plot_bgcolor="#0d1b2a", font_color="#fff",
    height=400,
)
st.plotly_chart(fig_radar, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — Category Scores
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📈 8. Category Scores</div>', unsafe_allow_html=True)

df_cat = pd.DataFrame({
    "Category": radar_labels,
    "Proposal A": [round(scores["cat_a"].get(k, 0), 1) for k in radar_keys],
    "Proposal B": [round(scores["cat_b"].get(k, 0), 1) for k in radar_keys],
})
fig_bar = px.bar(
    df_cat, x="Category", y=["Proposal A", "Proposal B"],
    barmode="group",
    color_discrete_map={"Proposal A": "#4fc3f7", "Proposal B": "#66bb6a"},
    labels={"value": "Score (0–100)", "variable": "Proposal"},
)
fig_bar.update_layout(
    paper_bgcolor="#0d1b2a", plot_bgcolor="#0d1b2a",
    font_color="#fff", yaxis_range=[0, 100], height=350,
)
st.plotly_chart(fig_bar, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — Overall Score
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">🏆 9. Overall UrbanGrid Score</div>', unsafe_allow_html=True)

fig_total = go.Figure(data=[
    go.Bar(name="Proposal A", x=["Overall Score"], y=[round(scores["total_a"],1)],
           marker_color="#4fc3f7", text=[f"{scores['total_a']:.1f}"], textposition="outside"),
    go.Bar(name="Proposal B", x=["Overall Score"], y=[round(scores["total_b"],1)],
           marker_color="#66bb6a", text=[f"{scores['total_b']:.1f}"], textposition="outside"),
])
fig_total.update_layout(
    barmode="group", yaxis_range=[0, 110], height=320,
    paper_bgcolor="#0d1b2a", plot_bgcolor="#0d1b2a",
    font_color="#fff", yaxis_title="Score (0–100)",
)
st.plotly_chart(fig_total, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 10 — Recommended Proposal
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">🎯 10. Recommended Proposal</div>', unsafe_allow_html=True)

winner_label = scores["winner"]
winner_score = scores["total_a"] if winner_label == "Proposal A" else scores["total_b"]
loser_score  = scores["total_b"] if winner_label == "Proposal A" else scores["total_a"]

st.markdown(f"""
<div class="recommendation-box">
  <h2 style="margin:0 0 .5rem;">🏅 RECOMMENDED: {winner_label}</h2>
  <p style="font-size:1.2rem;margin:0 0 .8rem;">
    Estimated Score: <strong>{winner_score:.1f}</strong> &nbsp;|&nbsp;
    Difference: <strong>+{scores['diff']:.1f}</strong>
  </p>
  <p style="font-size:.9rem;">
    {scores['recommendation'].replace(chr(10), '<br>')}
  </p>
</div>
<p style="font-size:.75rem;color:#888;margin-top:.5rem;">
  Recommendation depends on the configured scoring weights and supplied/estimated data.
</p>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 11 — Planning Priorities (Trade-off Explorer)
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">⚖️ 11. Planning Priorities – Trade-off Explorer</div>', unsafe_allow_html=True)
st.caption("Decision support based on configurable priorities. Weights are already applied above from the sidebar.")

# Show how relative ranking changes
priority_data = pd.DataFrame({
    "Category": radar_labels,
    "Weight (%)": [w_sus, w_day, w_liv, w_eff],
    "A Score": [round(scores["cat_a"].get(k),1) for k in radar_keys],
    "B Score": [round(scores["cat_b"].get(k),1) for k in radar_keys],
    "A Contribution": [round(scores["cat_a"].get(k)*weights[k]/max(w_total,1),1) for k in radar_keys],
    "B Contribution": [round(scores["cat_b"].get(k)*weights[k]/max(w_total,1),1) for k in radar_keys],
})
st.dataframe(priority_data, use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 12 — What-If Optimization
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">🔬 12. What-If Optimization</div>', unsafe_allow_html=True)
st.caption("Scenario estimate – not a Forma simulation.")

if any_wi and scores_wi:
    base_a = scores["total_a"]
    wi_a   = scores_wi["total_a"]
    delta  = wi_a - base_a

    wi_cols = st.columns(3)
    kpi(wi_cols[0], "Current Score (A)", f"{base_a:.1f}")
    kpi(wi_cols[1], "Scenario Score (A)", f"{wi_a:.1f}")
    kpi(wi_cols[2], "Score Change", f"{'+'if delta>=0 else ''}{delta:.1f}")

    # Which KPIs changed?
    changed = []
    for k in ["green_percentage", "avg_building_height", "ground_coverage", "road_density"]:
        orig = metrics_a.get(k, 0)
        new  = metrics_a_wi.get(k, 0)
        if orig != new:
            dir_icon = "↑" if new > orig else "↓"
            changed.append({"Parameter": k.replace("_"," ").title(),
                            "Original": f"{orig:.1f}", "Scenario": f"{new:.1f}", "Change": dir_icon})
    if changed:
        st.dataframe(pd.DataFrame(changed), use_container_width=True, hide_index=True)
else:
    st.info("Use the **What-If Scenario** sliders in the sidebar to explore parameter changes on Proposal A.")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 13 — Selected Proposal & Export
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">💾 13. Export / Revit Handoff</div>', unsafe_allow_html=True)

winner_metrics = metrics_a if winner_label == "Proposal A" else metrics_b
winner_gdf     = gdf_a if winner_label == "Proposal A" else gdf_b
winner_name    = winner_label

ex1, ex2, ex3, ex4 = st.columns(4)

with ex1:
    geo = exp.geojson_download(winner_gdf) if winner_gdf is not None else '{"type":"FeatureCollection","features":[]}'
    st.download_button("📥 Winning GeoJSON", geo, f"{winner_name.lower().replace(' ','_')}.geojson", "application/json")

with ex2:
    st.download_button("📄 Winner Metrics CSV", exp.metrics_to_csv(winner_metrics), "winner_metrics.csv", "text/csv")

with ex3:
    st.download_button("📊 Comparison CSV", exp.comparison_csv(metrics_a, metrics_b), "comparison.csv", "text/csv")

with ex4:
    zip_bytes = exp.revit_handoff_zip(winner_gdf, site_gdf, winner_metrics, winner_name)
    st.download_button("🏗️ Revit Handoff ZIP", zip_bytes, "revit_handoff.zip", "application/zip")

st.markdown("""
<div class="workflow-box" style="margin-top:1rem;">
  Selected Forma Proposal<br>
  &nbsp;&nbsp;→ Export structured data from UrbanGrid<br>
  &nbsp;&nbsp;→ Import buildings.csv / site.geojson into Autodesk Revit<br>
  &nbsp;&nbsp;→ Develop detailed buildings, MEP systems, documentation<br>
  &nbsp;&nbsp;→ Sync final Revit model back to Forma for site presentation
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# Footer
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="footer">Team Urban Bharat &nbsp;|&nbsp; SIH 2026 &nbsp;|&nbsp; Problem Statement 26114</div>', unsafe_allow_html=True)
