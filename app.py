"""
Dancing with the SARs — Myanmar SAR Change Detector
+ featured case study: 2025 Sagaing Fault earthquake (Myanmar)

Run:  streamlit run app.py
Needs: pip install streamlit streamlit-folium earthengine-api folium rasterio numpy matplotlib
"""
import os
import json
import datetime as dt
import numpy as np
import streamlit as st
import ee
import folium
from streamlit_folium import st_folium

# ============ FILL THESE IN ============
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

st.set_page_config(page_title="Dancing with the SARs — Myanmar", page_icon="🛰️", layout="wide")

@st.cache_resource
def init_ee():
    ee.Initialize(project=GEE_PROJECT)

try:
    init_ee()
except Exception as e:
    st.error(f"Google Earth Engine failed to initialise (project: `{GEE_PROJECT}`).\n\n"
             "1. Set `GEE_PROJECT` at the top of app.py to your GEE-registered Cloud project ID.\n"
             "2. Run `earthengine authenticate` once in a terminal.\n\n"
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
st.sidebar.title("🛰️ Myanmar SAR Change Detector")
st.sidebar.caption("Click anywhere in Myanmar. Radar compares before vs after.")

st.sidebar.markdown("**Quick Preset Locations**")
col_b1, col_b2 = st.sidebar.columns(2)
if col_b1.button("⭐ Mandalay (Quake)"):
    st.session_state.pin = (21.97, 96.08)
    st.session_state.dates = (dt.date(2025, 3, 1), dt.date(2025, 3, 27),
                              dt.date(2025, 3, 29), dt.date(2025, 4, 20))
    st.session_state.outside_warning = False
    st.session_state.zoomed = True
    st.rerun()

if col_b2.button("📍 Yangon"):
    st.session_state.pin = (16.8661, 96.1951)
    st.session_state.outside_warning = False
    st.session_state.zoomed = True
    st.rerun()

if st.sidebar.button("📍 Naypyidaw"):
    st.session_state.pin = (19.7633, 96.0785)
    st.session_state.outside_warning = False
    st.session_state.zoomed = True
    st.rerun()

d = st.session_state.dates
b1 = st.sidebar.date_input("Before: from", d[0])
b2 = st.sidebar.date_input("Before: to", d[1])
a1 = st.sidebar.date_input("After: from", d[2])
a2 = st.sidebar.date_input("After: to", d[3])
st.session_state.dates = (b1, b2, a1, a2)

radius_km = st.sidebar.slider("Analysis radius (km)", 1, 10, 5)
thresh_db = st.sidebar.slider("Change threshold (dB)", 1.5, 6.0, 3.0, 0.5)

has_ifg = os.path.exists(IFG_TIF)
show_ifg = st.sidebar.checkbox("Show interferogram (northern Sagaing Fault)", value=False) if has_ifg else False

has_nisar = os.path.exists(NISAR_PNG) and os.path.exists(NISAR_JSON)
show_nisar = st.sidebar.checkbox("Show NISAR L-band sample layer", value=False) if has_nisar else False

# ---------- GEE analysis ----------
def s1_median(roi, start, end):
    return (ee.ImageCollection("COPERNICUS/S1_GRD")
            .filterBounds(roi).filterDate(str(start), str(end))
            .filter(ee.Filter.eq("instrumentMode", "IW"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
            .select("VV"))

@st.cache_data(show_spinner="Running radar analysis…")
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

# ---------- Layout ----------
st.title("Dancing with the SARs — Myanmar")
st.caption("Satellite radar sees through clouds, day and night. Drop a pin anywhere in Myanmar to detect surface change.")

if st.session_state.get("outside_warning"):
    st.warning("⚠️ That click was outside Myanmar. Please drop a pin within Myanmar boundaries (lat 9.5°–28.6° N, lon 92.1°–101.2° E).")

col_map, col_stats = st.columns([7, 3])

with col_map:
    # Myanmar lock: overview at center 21.0, 96.0, zoom 6, bounds constrained.
    # Zoom in once a pin/preset is chosen so the circle and change layer are visible;
    # jump to the interferogram footprint when it is switched on (it lies north of Mandalay).
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
            folium.TileLayer(url, attr="Copernicus Sentinel-1 via Google Earth Engine",
                             name=name, overlay=True, show=name.startswith("Change")).add_to(m)

    # Optional LiCSAR interferogram
    if has_ifg:
        folium.raster_layers.ImageOverlay(
            img_ifg,
            bounds=bounds_ifg,
            opacity=0.7,
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

    folium.Circle([lat, lon], radius=radius_km * 1000, color="#ffcc00", fill=False, weight=2).add_to(m)
    folium.Marker([lat, lon], tooltip=f"Selected: {lat:.4f}, {lon:.4f}").add_to(m)
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

with col_stats:
    st.subheader("📊 Estimated Change in Area")
    st.write(f"📍 {lat:.4f}, {lon:.4f} · Radius {radius_km} km")
    if not res["ok"]:
        st.error(f"No Sentinel-1 images found (before: {res['nb']}, after: {res['na']}). "
                 "Widen the date ranges.")
    else:
        tot = res["total"]
        st.metric("Estimated brighter area (new structures, debris, rough ground)",
                  f"{res['brighter']:.2f} km²", f"{100*res['brighter']/tot:.1f}% of area")
        st.metric("Estimated darker area (water, flattened or smoothed surfaces)",
                  f"{res['darker']:.2f} km²", f"{100*res['darker']/tot:.1f}% of area")
        st.caption(f"Estimated from {res['nb']} before and {res['na']} after Sentinel-1 (ESA) images. Threshold ±{thresh_db} dB. All values are radar estimates, not ground truth surveys.")

    st.markdown("---")
    with st.expander("How to read radar change", expanded=True):
        st.write("""
- Radar measures backscatter (how much signal bounces back).
- **Brighter** = rougher or more vertical: new buildings, collapsed debris, cracked ground.
- **Darker** = smoother: standing water, flattened areas.
- Penetrates clouds and functions day or night — unlike optical satellites.
""")
    with st.expander("⭐ Case study: the Sagaing Fault"):
        if has_ifg:
            st.write(f"""
- **28 March 2025, M7.7**: Major strike-slip earthquake rupturing ~500 km of the Sagaing Fault.
- The interferogram layer is a Sentinel-1 (ESA) frame processed by COMET LiCSAR over the
  **northern Sagaing Fault (~24.2–26.9° N)**, north of Mandalay. It compares radar **phase** before and after (24 Mar – 5 Apr 2025).
- **One colour cycle = {WAVELENGTH*100/2:.1f} cm** of ground movement toward/away from the satellite (line of sight).
- Phase shows *how far the ground moved* along that line of sight, which brightness change alone cannot.
  The drop-a-pin stats above are brightness change only.
""")
        else:
            st.write("""
- **28 March 2025, M7.7**: Major strike-slip earthquake along the Sagaing Fault near Mandalay.
- Amplitude change detects surface disruption, debris, and ground upheaval.
- *(Interferogram phase data is optional and not currently loaded).*
""")
    with st.expander("Why NISAR"):
        st.write("""
- **Sentinel-1 (ESA)**: Operational C-band (5.5 cm) providing regular observations via Google Earth Engine.
- **NISAR (NASA-ISRO)**: L-band (24 cm) penetrates dense vegetation canopy and resolves larger displacements (~12 cm per fringe).
- **Capability sample**: NISAR launched in July 2025 (after the March 2025 earthquake); the NISAR layer in this tool is an illustrative sample acquired 4 Oct 2026 demonstrating L-band capability, **not** earthquake-event data.
- NISAR will map global land surfaces every 12 days, enabling routine L-band monitoring.
""")

    # Dynamic data sources attribution
    sources = ["Copernicus Sentinel-1 (ESA) via Google Earth Engine"]
    if has_ifg and show_ifg:
        sources.append("COMET LiCSAR interferogram of Sentinel-1 data, northern Sagaing Fault (24 Mar – 5 Apr 2025)")
    if has_nisar and show_nisar:
        sources.append("NASA-ISRO NISAR via ASF (acquired 4 Oct 2026)")
    st.caption("Data: " + "; ".join(sources) + ".")
