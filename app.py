"""
Dancing with the SARs — Drop-a-Pin SAR Change Detector (global)
+ featured case study: 2025 Sagaing Fault earthquake (Myanmar)

Run:  streamlit run app.py
Needs: pip install streamlit streamlit-folium earthengine-api folium rasterio numpy matplotlib
"""
import os
import datetime as dt
import numpy as np
import streamlit as st
import ee
import folium
from streamlit_folium import st_folium

# ============ FILL THESE IN ============
GEE_PROJECT = "engaged-oarlock-432211-q9"
IFG_TIF     = "data/geo.unw.tif"     # optional: LiCSAR interferogram for the Sagaing case study
WAVELENGTH  = 0.0555                 # Sentinel-1 C-band (m). NISAR L-band = 0.242
# =======================================

st.set_page_config(page_title="Dancing with the SARs", page_icon="🛰️", layout="wide")

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

# ---------- Sidebar ----------
st.sidebar.title("🛰️ SAR Change Detector")
st.sidebar.caption("Click anywhere on Earth. Radar compares before vs after.")

if st.sidebar.button("⭐ Case study: 2025 Myanmar earthquake"):
    st.session_state.pin = (21.97, 96.08)
    st.session_state.dates = (dt.date(2025, 3, 1), dt.date(2025, 3, 27),
                              dt.date(2025, 3, 29), dt.date(2025, 4, 20))

d = st.session_state.dates
b1 = st.sidebar.date_input("Before: from", d[0])
b2 = st.sidebar.date_input("Before: to", d[1])
a1 = st.sidebar.date_input("After: from", d[2])
a2 = st.sidebar.date_input("After: to", d[3])
st.session_state.dates = (b1, b2, a1, a2)

radius_km = st.sidebar.slider("Analysis radius (km)", 1, 10, 5)
thresh_db = st.sidebar.slider("Change threshold (dB)", 1.5, 6.0, 3.0, 0.5)
show_ifg  = st.sidebar.checkbox("Show earthquake interferogram (case study)", os.path.exists(IFG_TIF))

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

# ---------- Optional interferogram overlay ----------
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

# ---------- Layout ----------
st.title("Dancing with the SARs")
st.caption("Radar sees through clouds, day and night. Drop a pin to see what changed on the ground.")
col_map, col_stats = st.columns([7, 3])

with col_map:
    m = folium.Map(location=[lat, lon], zoom_start=12, tiles="OpenStreetMap")
    if res["ok"]:
        for name, url in res["tiles"].items():
            folium.TileLayer(url, attr="Copernicus Sentinel-1 via Google Earth Engine",
                             name=name, overlay=True, show=name.startswith("Change")).add_to(m)
    if show_ifg and os.path.exists(IFG_TIF):
        img, bounds = load_ifg(IFG_TIF)
        folium.raster_layers.ImageOverlay(img, bounds=bounds, opacity=0.7, mercator_project=True,
                                          name="Earthquake interferogram (fringes)").add_to(m)
    folium.Circle([lat, lon], radius=radius_km * 1000, color="#ffcc00", fill=False, weight=2).add_to(m)
    folium.Marker([lat, lon], tooltip=f"{lat:.4f}, {lon:.4f}").add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    out = st_folium(m, height=620, use_container_width=True, returned_objects=["last_clicked"])
    if out and out.get("last_clicked"):
        new_pin = (round(out["last_clicked"]["lat"], 4), round(out["last_clicked"]["lng"], 4))
        if new_pin != st.session_state.pin:
            st.session_state.pin = new_pin
            st.rerun()

with col_stats:
    st.subheader("📊 Change in this area")
    st.write(f"📍 {lat:.4f}, {lon:.4f} · radius {radius_km} km")
    if not res["ok"]:
        st.error(f"No Sentinel-1 images found (before: {res['nb']}, after: {res['na']}). "
                 "Widen the date ranges.")
    else:
        tot = res["total"]
        st.metric("Got brighter (new structures, debris, rough ground)",
                  f"{res['brighter']:.2f} km²", f"{100*res['brighter']/tot:.1f}% of area")
        st.metric("Got darker (water, flattened or smoothed surfaces)",
                  f"{res['darker']:.2f} km²", f"{100*res['darker']/tot:.1f}% of area")
        st.caption(f"Images used: {res['nb']} before, {res['na']} after. Threshold ±{thresh_db} dB.")

    st.markdown("---")
    with st.expander("How to read radar change", expanded=True):
        st.write("""
- Radar measures how much signal bounces back.
- **Brighter** = rougher or more vertical: new buildings, collapsed debris, cracked ground.
- **Darker** = smoother: water, flattened areas.
- Works through clouds and at night — optical satellites can't.
""")
    with st.expander("⭐ Case study: the Sagaing Fault"):
        st.write(f"""
- 28 March 2025, M7.7. The fault ruptured for ~500 km.
- The interferogram layer compares radar **phase** before/after.
  **One colour cycle = {WAVELENGTH*100/2:.1f} cm** of ground movement toward/away from the satellite (line of sight).
- This shows *how far the ground moved*, which brightness change alone can't.
""")
    with st.expander("Why NISAR"):
        st.write("""
- Sentinel-1 (C-band, 5.5 cm) is our current data source.
- NISAR's L-band (24 cm) sees through vegetation and handles bigger motions (~12 cm per fringe).
- NISAR images Earth's land every 12 days — this same tool can run on NISAR data as it becomes available.
""")
    st.caption("Data: Copernicus Sentinel-1 (ESA) via Google Earth Engine; COMET LiCSAR interferogram.")
