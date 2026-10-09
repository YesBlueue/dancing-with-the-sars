"""
Dancing with the SARs — Myanmar SAR Change Detector
+ featured case study: 2025 Sagaing Fault earthquake (Myanmar)

Run:  streamlit run app.py
Needs: pip install streamlit streamlit-folium earthengine-api folium rasterio numpy matplotlib pandas
"""
import os
import json
import datetime as dt
import numpy as np
import pandas as pd
import streamlit as st
import ee
import folium
from streamlit_folium import st_folium

# ============ CONFIGURATION ============
GEE_PROJECT = "engaged-oarlock-432211-q9"
IFG_TIF     = "data/geo.unw.tif"     # optional: LiCSAR interferogram for the Sagaing case study
NISAR_PNG   = "data/nisar.png"       # optional: NISAR sample PNG
NISAR_JSON  = "data/nisar_bounds.json"
WAVELENGTH  = 0.0555                 # Sentinel-1 C-band (m). NISAR L-band = 0.242

# Myanmar geographical bounds lock
MYANMAR_MIN_LAT, MYANMAR_MAX_LAT = 9.5, 28.6
MYANMAR_MIN_LON, MYANMAR_MAX_LON = 92.1, 101.2
MYANMAR_CENTER = (21.0, 96.0)
# =======================================

st.set_page_config(
    page_title="Dancing with the SARs — Myanmar",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Glassmorphism, Modern Typography, Sleek Badges)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

h1, h2, h3, h4, .stTitle {
    font-family: 'Outfit', sans-serif !important;
    letter-spacing: -0.02em;
}

/* Glassmorphic cards */
.metric-card {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 14px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
    backdrop-filter: blur(8px);
}

.legend-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 12px;
    border-radius: 6px;
    background: linear-gradient(90deg, #0000ff 0%, #ffffff 50%, #ff0000 100%);
    margin: 8px 0;
    box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.4);
}

.fringe-bar {
    display: flex;
    height: 12px;
    border-radius: 6px;
    background: linear-gradient(90deg, #ff0000 0%, #ffff00 20%, #00ff00 40%, #00ffff 60%, #0000ff 80%, #ff00ff 100%);
    margin: 8px 0;
    box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.4);
}

.status-badge {
    display: inline-block;
    padding: 3px 9px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-right: 6px;
    margin-bottom: 6px;
}
.badge-active { background: rgba(0, 230, 118, 0.15); color: #00e676; border: 1px solid rgba(0, 230, 118, 0.3); }
.badge-info { background: rgba(0, 176, 255, 0.15); color: #00b0ff; border: 1px solid rgba(0, 176, 255, 0.3); }
.badge-warning { background: rgba(255, 171, 0, 0.15); color: #ffab00; border: 1px solid rgba(255, 171, 0, 0.3); }

/* Quick scenario buttons */
div[data-testid="stSidebar"] button {
    border-radius: 8px;
    transition: all 0.2s ease;
}
div[data-testid="stSidebar"] button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0, 176, 255, 0.25);
}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_ee():
    ee.Initialize(project=GEE_PROJECT)

try:
    init_ee()
except Exception as e:
    st.error(f"Google Earth Engine failed to initialise (project: `{GEE_PROJECT}`).\n\n"
             "1. Ensure your Google Cloud account is granted access to the project.\n"
             "2. Run `earthengine authenticate` in your terminal.\n\n"
             f"Details: {e}")
    st.stop()

# ---------- State ----------
if "pin" not in st.session_state:
    st.session_state.pin = (21.97, 96.08)          # Mandalay
if "dates" not in st.session_state:
    st.session_state.dates = (dt.date(2025, 3, 1), dt.date(2025, 3, 27),
                              dt.date(2025, 3, 29), dt.date(2025, 4, 20))
if "outside_warning" not in st.session_state:
    st.session_state.outside_warning = False
if "zoomed" not in st.session_state:
    st.session_state.zoomed = False      # False: Myanmar overview (zoom 6); True: zoom to the pin
if "last_click" not in st.session_state:
    st.session_state.last_click = None   # last map click already handled (st_folium repeats it every rerun)

# ---------- Sidebar ----------
st.sidebar.title("🛰️ Myanmar SAR Monitor")
st.sidebar.caption("All-weather radar observation across Myanmar using microwave backscatter and interferometry.")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎯 Quick Scenarios")

col_sc1, col_sc2 = st.sidebar.columns(2)
if col_sc1.button("🌋 Mandalay Quake", use_container_width=True):
    st.session_state.pin = (21.97, 96.08)
    st.session_state.dates = (dt.date(2025, 3, 1), dt.date(2025, 3, 27),
                              dt.date(2025, 3, 29), dt.date(2025, 4, 20))
    st.session_state.outside_warning = False
    st.session_state.zoomed = True
    st.rerun()

if col_sc2.button("🏙️ Yangon Delta", use_container_width=True):
    st.session_state.pin = (16.8661, 96.1951)
    st.session_state.dates = (dt.date(2025, 3, 1), dt.date(2025, 3, 27),
                              dt.date(2025, 3, 29), dt.date(2025, 4, 20))
    st.session_state.outside_warning = False
    st.session_state.zoomed = True
    st.rerun()

if st.sidebar.button("🏛️ Naypyidaw Capital Corridor", use_container_width=True):
    st.session_state.pin = (19.7633, 96.0785)
    st.session_state.dates = (dt.date(2025, 3, 1), dt.date(2025, 3, 27),
                              dt.date(2025, 3, 29), dt.date(2025, 4, 20))
    st.session_state.outside_warning = False
    st.session_state.zoomed = True
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 📅 Temporal Windows")
d = st.session_state.dates
b1 = st.sidebar.date_input("Before: start", d[0])
b2 = st.sidebar.date_input("Before: end", d[1])
a1 = st.sidebar.date_input("After: start", d[2])
a2 = st.sidebar.date_input("After: end", d[3])
st.session_state.dates = (b1, b2, a1, a2)

st.sidebar.markdown("### ⚙️ Analysis Parameters")
radius_km = st.sidebar.slider("Analysis radius (km)", 1, 10, 5, help="Radius around the pin to buffer and calculate change statistics.")
thresh_db = st.sidebar.slider("Change threshold (±dB)", 1.5, 6.0, 3.0, 0.5, help="Threshold backscatter deviation in decibels to classify surface alteration.")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🛰️ Optional Map Overlays")

has_ifg = os.path.exists(IFG_TIF)
show_ifg = st.sidebar.checkbox(
    "🌈 LiCSAR Fringes (northern Sagaing Fault)",
    value=False,
    disabled=not has_ifg,
    help="Sentinel-1 unwrapped-phase interferogram (COMET LiCSAR), 24 Mar – 5 Apr 2025, covering ~24.2–26.9° N (north of Mandalay)."
) if has_ifg else False

has_nisar = os.path.exists(NISAR_PNG) and os.path.exists(NISAR_JSON)
show_nisar = st.sidebar.checkbox(
    "📡 NISAR L-Band Sample Layer",
    value=False,
    disabled=not has_nisar,
    help="Displays NASA-ISRO NISAR L-band sample backscatter acquired 4 Oct 2026."
) if has_nisar else False

# Status Pills in Sidebar
st.sidebar.markdown("""
<div style='margin-top: 15px;'>
    <span class='status-badge badge-active'>● Sentinel-1 Operational</span>
    """ + (f"<span class='status-badge badge-info'>● LiCSAR Loaded</span>" if has_ifg else "") + """
    """ + (f"<span class='status-badge badge-warning'>● NISAR Sample Ready</span>" if has_nisar else "") + """
</div>
""", unsafe_allow_html=True)

# ---------- GEE analysis ----------
def s1_median(roi, start, end):
    return (ee.ImageCollection("COPERNICUS/S1_GRD")
            .filterBounds(roi).filterDate(str(start), str(end))
            .filter(ee.Filter.eq("instrumentMode", "IW"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
            .select("VV"))

@st.cache_data(show_spinner="Computing satellite radar change across Myanmar…")
def analyze(lat, lon, r_km, b1, b2, a1, a2, t):
    roi = ee.Geometry.Point([lon, lat]).buffer(r_km * 1000)
    bc, ac = s1_median(roi, b1, b2), s1_median(roi, a1, a2)
    nb, na = bc.size().getInfo(), ac.size().getInfo()
    if nb == 0 or na == 0:
        return {"ok": False, "nb": nb, "na": na}
    before = bc.median().clip(roi).focal_median(30, "circle", "meters")
    after  = ac.median().clip(roi).focal_median(30, "circle", "meters")
    diff = after.subtract(before)
    brighter = diff.gt(t).selfMask()
    darker   = diff.lt(-t).selfMask()
    px = ee.Image.pixelArea().divide(1e6)
    stats = ee.Dictionary({
        "brighter": brighter.multiply(px).reduceRegion(ee.Reducer.sum(), roi, 20, maxPixels=1e9).get("VV"),
        "darker":   darker.multiply(px).reduceRegion(ee.Reducer.sum(), roi, 20, maxPixels=1e9).get("VV"),
        "total":    px.reduceRegion(ee.Reducer.sum(), roi, 20, maxPixels=1e9).get("area"),
    }).getInfo()
    vis_sar  = {"min": -25, "max": 0}
    vis_diff = {"min": -6, "max": 6, "palette": ["0000ff", "ffffff", "ff0000"]}
    return {
        "ok": True, "nb": nb, "na": na,
        "brighter": stats["brighter"] or 0, "darker": stats["darker"] or 0, "total": stats["total"],
        "tiles": {
            "Before (radar)": before.getMapId(vis_sar)["tile_fetcher"].url_format,
            "After (radar)":  after.getMapId(vis_sar)["tile_fetcher"].url_format,
            "Change (red=brighter, blue=darker)": diff.getMapId(vis_diff)["tile_fetcher"].url_format,
        },
    }

lat, lon = st.session_state.pin
res = analyze(lat, lon, radius_km, b1, b2, a1, a2, thresh_db)

# ---------- Optional interferogram & NISAR overlays ----------
@st.cache_data
def load_ifg(path, max_px=2000):
    import rasterio
    from rasterio.enums import Resampling
    import matplotlib.cm as cm
    with rasterio.open(path) as src:
        s = max(src.width, src.height) / max_px
        h, w = int(src.height / max(s, 1)), int(src.width / max(s, 1))
        arr = src.read(1, out_shape=(h, w), resampling=Resampling.average).astype("float32")
        if src.nodata is not None:
            arr[arr == src.nodata] = np.nan
        b = src.bounds
    arr[arr == 0] = np.nan
    wrapped = np.mod(arr, 2 * np.pi) / (2 * np.pi)
    rgba = cm.hsv(np.nan_to_num(wrapped))
    rgba[np.isnan(arr), 3] = 0
    return (rgba * 255).astype("uint8"), [[b.bottom, b.left], [b.top, b.right]]

@st.cache_data
def load_nisar(png_path, json_path):
    import matplotlib.pyplot as plt
    img = (plt.imread(png_path) * 255).astype("uint8")
    with open(json_path, "r") as fp:
        meta = json.load(fp)
    return img, meta["bounds"]

# ---------- Main View ----------
st.title("🛰️ Dancing with the SARs — Myanmar")
st.markdown("##### Cloud-Penetrating Synthetic Aperture Radar (SAR) Surface Change Detection")

if st.session_state.get("outside_warning"):
    st.warning("⚠️ The clicked location was outside Myanmar. The map is constrained to Myanmar territory (lat 9.5°–28.6° N, lon 92.1°–101.2° E).")

col_map, col_stats = st.columns([7, 3])

with col_map:
    # Leaflet Map with Myanmar Geographical Lock: overview at zoom 6, zoom to the pin once one
    # is chosen, and jump to the interferogram footprint when it is switched on (north of Mandalay).
    if has_ifg:
        img_ifg, bounds_ifg = load_ifg(IFG_TIF)
    if show_ifg:
        (s_, w_), (n_, e_) = bounds_ifg
        view, zoom = [(s_ + n_) / 2, (w_ + e_) / 2], 8
    elif st.session_state.zoomed:
        view, zoom = [lat, lon], 11
    else:
        view, zoom = list(MYANMAR_CENTER), 6
    m = folium.Map(
        location=view,
        zoom_start=zoom,
        min_zoom=5,
        max_bounds=True,
        min_lat=MYANMAR_MIN_LAT,
        max_lat=MYANMAR_MAX_LAT,
        min_lon=MYANMAR_MIN_LON,
        max_lon=MYANMAR_MAX_LON,
        tiles="OpenStreetMap"
    )

    if res["ok"]:
        for name, url in res["tiles"].items():
            folium.TileLayer(
                url,
                attr="Copernicus Sentinel-1 via Google Earth Engine",
                name=name,
                overlay=True,
                show=name.startswith("Change")
            ).add_to(m)

    # Optional LiCSAR interferogram
    if has_ifg:
        folium.raster_layers.ImageOverlay(
            img_ifg,
            bounds=bounds_ifg,
            opacity=0.75,
            mercator_project=True,
            name="Sentinel-1 interferogram, northern Sagaing Fault (fringes)",
            show=show_ifg
        ).add_to(m)

    # Optional NISAR sample layer
    if has_nisar:
        img_nisar, bounds_nisar = load_nisar(NISAR_PNG, NISAR_JSON)
        folium.raster_layers.ImageOverlay(
            img_nisar,
            bounds=bounds_nisar,
            opacity=0.8,
            mercator_project=True,
            name="NISAR L-band (sample)",
            show=show_nisar,
            attr="NASA-ISRO NISAR via ASF"
        ).add_to(m)

    folium.Circle(
        [lat, lon],
        radius=radius_km * 1000,
        color="#00e676",
        fill=True,
        fill_color="#00e676",
        fill_opacity=0.1,
        weight=2
    ).add_to(m)

    folium.Marker(
        [lat, lon],
        tooltip=f"Selected Location: {lat:.4f}° N, {lon:.4f}° E",
        icon=folium.Icon(color="red", icon="crosshairs", prefix="fa")
    ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    out = st_folium(m, height=620, use_container_width=True, returned_objects=["last_clicked"])
    if out and out.get("last_clicked"):
        click_lat = round(out["last_clicked"]["lat"], 4)
        click_lng = round(out["last_clicked"]["lng"], 4)
        new_click = (click_lat, click_lng)
        if new_click != st.session_state.last_click:
            st.session_state.last_click = new_click
            if MYANMAR_MIN_LAT <= click_lat <= MYANMAR_MAX_LAT and MYANMAR_MIN_LON <= click_lng <= MYANMAR_MAX_LON:
                st.session_state.pin = new_click
                st.session_state.outside_warning = False
                st.session_state.zoomed = True
            else:
                st.session_state.outside_warning = True
            st.rerun()

    # Visual Legends beneath Map
    st.markdown("""
    <div style='background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.07); border-radius: 8px; padding: 12px 16px; margin-top: 10px;'>
        <div style='display: flex; justify-content: space-between; font-size: 0.8rem; font-weight: 500;'>
            <span style='color: #448aff;'>◀ Darker (-dB: water, flat surfaces)</span>
            <span style='color: #888;'>Neutral (0 dB: unchanged)</span>
            <span style='color: #ff5252;'>Brighter (+dB: debris, upheaval) ▶</span>
        </div>
        <div class='legend-bar'></div>
    </div>
    """, unsafe_allow_html=True)

    if show_ifg and has_ifg:
        st.markdown(f"""
        <div style='background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.07); border-radius: 8px; padding: 12px 16px; margin-top: 8px;'>
            <div style='display: flex; justify-content: space-between; font-size: 0.8rem; font-weight: 500;'>
                <span>0</span>
                <span style='color: #00e676;'>Wrapped phase: one full colour cycle (0 → 2π) ≈ {WAVELENGTH*100/2:.1f} cm line-of-sight motion</span>
                <span>2π</span>
            </div>
            <div class='fringe-bar'></div>
        </div>
        """, unsafe_allow_html=True)

with col_stats:
    st.markdown(f"""
    <div class='metric-card'>
        <div style='font-size: 0.85rem; color: #888; text-transform: uppercase; letter-spacing: 0.05em;'>Analysis Focal Region</div>
        <div style='font-size: 1.25rem; font-weight: 600; margin-top: 4px;'>📍 {lat:.4f}° N, {lon:.4f}° E</div>
        <div style='font-size: 0.9rem; color: #aaa; margin-top: 2px;'>Radius: <b>{radius_km} km</b> · Threshold: <b>±{thresh_db} dB</b></div>
    </div>
    """, unsafe_allow_html=True)

    if not res["ok"]:
        st.error(f"No Sentinel-1 images found in this temporal window (before: {res['nb']}, after: {res['na']}). Try widening the date ranges.")
    else:
        tot = res["total"]
        brighter_pct = 100 * res["brighter"] / tot
        darker_pct = 100 * res["darker"] / tot
        unchanged = max(0, tot - res["brighter"] - res["darker"])
        unchanged_pct = 100 * unchanged / tot

        st.metric(
            label="Estimated Brighter (Debris, Fissures, Structures)",
            value=f"{res['brighter']:.2f} km²",
            delta=f"{brighter_pct:.1f}% of region",
            delta_color="inverse"
        )

        st.metric(
            label="Estimated Darker (Standing Water, Flattened)",
            value=f"{res['darker']:.2f} km²",
            delta=f"{darker_pct:.1f}% of region",
            delta_color="off"
        )

        # Visual Area Breakdown Chart
        chart_data = pd.DataFrame({
            "Classification": ["Brighter (+dB)", "Darker (-dB)", "Unchanged"],
            "Area (km²)": [round(res["brighter"], 2), round(res["darker"], 2), round(unchanged, 2)],
        })

        st.caption("Surface Change Proportional Breakdown:")
        st.bar_chart(chart_data.set_index("Classification"), height=160, color="#00b0ff")

        st.caption(f"Estimated from {res['nb']} before and {res['na']} after Sentinel-1 (ESA) passes. Values are satellite backscatter estimates, not ground-truth damage surveys.")

        # Export Analysis Summary
        summary_payload = {
            "region": "Myanmar",
            "pin": {"latitude": lat, "longitude": lon},
            "radius_km": radius_km,
            "threshold_db": thresh_db,
            "temporal_window": {
                "before": [str(b1), str(b2)],
                "after": [str(a1), str(a2)]
            },
            "metrics": {
                "total_area_km2": round(tot, 2),
                "brighter_km2": round(res["brighter"], 2),
                "darker_km2": round(res["darker"], 2),
                "brighter_percentage": round(brighter_pct, 1),
                "darker_percentage": round(darker_pct, 1)
            },
            "satellite_passes": {"before_count": res["nb"], "after_count": res["na"]}
        }

        st.download_button(
            label="📥 Export Analysis Summary (JSON)",
            data=json.dumps(summary_payload, indent=2),
            file_name=f"sar_analysis_{lat:.2f}_{lon:.2f}.json",
            mime="application/json",
            use_container_width=True
        )

    st.markdown("---")
    with st.expander("📖 How to read radar backscatter change", expanded=False):
        st.write("""
- **Backscatter**: Measures the microwave radar intensity reflected back to the sensor.
- **Brighter (+dB)**: Surface became rougher or more vertical (e.g. collapsed masonry, rubble, cracked earth, new structural surfaces).
- **Darker (-dB)**: Surface became smoother or absorbed microwaves (e.g. standing water, smooth sediment, cleared ground).
- **All-Weather Capability**: Penetrates dense clouds and darkness, delivering mission-critical situational awareness when optical satellites fail.
""")

    with st.expander("⭐ Case study: 2025 Sagaing Fault Earthquake", expanded=False):
        if has_ifg:
            st.write(f"""
- **28 March 2025, M7.7**: Severe strike-slip event along Myanmar's central tectonic artery.
- **Interferogram Phase (COMET LiCSAR, Sentinel-1)**: Spans 24 March – 5 April 2025 and covers the
  **northern Sagaing Fault (~24.2–26.9° N)**, north of Mandalay.
- **Color Fringes**: Each complete colour cycle represents **{WAVELENGTH*100/2:.1f} cm** of relative line-of-sight displacement.
- Phase maps *ground displacement distance*, whereas amplitude measures *surface roughness alterations*.
  The drop-a-pin statistics are amplitude (brightness) change only.
""")
        else:
            st.write("""
- **28 March 2025, M7.7**: Major strike-slip earthquake along the Sagaing Fault near Mandalay.
- Drop a pin along the fault to estimate backscatter (brightness) change before vs after the quake.
- *(Optional interferogram phase data can be loaded from `data/geo.unw.tif`).*
""")

    with st.expander("📡 Next-Generation Monitoring: Why NISAR", expanded=False):
        st.write("""
- **Sentinel-1 (ESA)**: Operational C-band (5.5 cm) providing regular observations via Google Earth Engine.
- **NISAR (NASA-ISRO)**: L-band (24 cm) penetrates dense vegetation canopy and resolves larger ground movements (~12 cm per fringe).
- **Illustrative Capability Sample**: NISAR launched in July 2025 (after the March 2025 earthquake); the NISAR layer in this app is a capability sample acquired 4 Oct 2026 demonstrating L-band backscatter, **not** earthquake-event data.
- NISAR will map global land surfaces every 12 days, enabling routine L-band monitoring.
""")

    # Dynamic data sources attribution
    sources = ["Copernicus Sentinel-1 (ESA) via Google Earth Engine"]
    if has_ifg and show_ifg:
        sources.append("COMET LiCSAR interferogram of Sentinel-1 data, northern Sagaing Fault (24 Mar – 5 Apr 2025)")
    if has_nisar and show_nisar:
        sources.append("NASA-ISRO NISAR via ASF (acquired 4 Oct 2026)")
    st.caption("Data: " + "; ".join(sources) + ".")
