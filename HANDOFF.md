# Handoff: Myanmar SAR Change Monitor (status at 13:44, Fri 9 Oct 2026)

For: the data teammate and their coding agent. Repo: https://github.com/YesBlueue/dancing-with-the-sars

**Deadlines (UTC+06:30): feature freeze 14:00, submission 15:00.**

## Roles
- **App owner** (frontend + backend, `app.py`): the teammate who wrote this handoff. Please don't edit `app.py` without coordinating with them, since they're changing it right now.
- **Data teammate**: prepares the files in `data/`. The app must run whether or not those files exist.

## Scope (Myanmar only)
Drop-a-pin SAR change monitor locked to Myanmar, plus a case study of the 28 Mar 2025 M7.7 Sagaing Fault earthquake at Mandalay. The app uses Sentinel-1 (ESA) brightness change from Google Earth Engine. Optional layers: the LiCSAR interferogram and a NISAR L-band sample. Out of scope: floods, crops, prediction, global coverage, population, accounts, alerts, GEE asset uploads.

## Done
- **App runs locally** (`python -m streamlit run app.py`, http://localhost:8501).
  - `GEE_PROJECT = "engaged-oarlock-432211-q9"`, and Earth Engine authentication has been done on the app owner's laptop.
  - Dependencies are installed (`requirements.txt`). `geemap` was dropped because it isn't needed.
- **Case study works with real computed numbers.** Mandalay (21.97, 96.08), 5 km radius, before 2025-03-01→03-27, after 2025-03-29→04-20, threshold ±3 dB:
  - 1.63 km² brighter (2.1%), 0.85 km² darker (1.1%).
  - 5 before images and 9 after images.
- **Map layers:** Before, After and Change (red = brighter, blue = darker) tiles from GEE, plus a pin and the radius circle.
- **Controls:** date pickers, radius slider (1–10 km) and threshold slider.
- **Errors handled:** if a date range has 0 images, the app shows an error instead of crashing. If GEE fails to start, it shows a readable error.
- **Explainer sections:** how to read radar change, the Sagaing case study, and why NISAR.
- **Interferogram overlay code already exists** (`load_ifg()` in `app.py`). It runs only if `data/geo.unw.tif` exists, and it hasn't been tested on a real file yet.
- **NISAR data delivered by the data teammate (thanks!):** `nisar_to_png.py`, `data/nisar.png` (2129×2084 RGBA, grayscale dB with a 2–98 percentile stretch), and `data/nisar_bounds.json`:
  - bounds `[[13.32, 91.47], [16.33, 94.65]]`, polarization `VVVV`
  - source: `NISAR_L2_PR_GCOV_..._20261004T231906_...h5` (acquired **4 Oct 2026**)

## Left to do (app owner, in order)
1. **Myanmar lock.** Centre (21.0, 96.0), zoom 6, max_bounds lat 9.5–28.6 and lon 92.1–101.2. Clicks outside Myanmar show a warning and are ignored. Myanmar title and wording.
2. **NISAR sample layer.** An ImageOverlay named "NISAR L-band (sample)", opacity 0.8, off by default. It's shown only if both files exist. Credit: "NASA-ISRO NISAR via ASF".
3. **Honesty fixes.**
   - Use "estimate" wording on the stats.
   - The sources caption should only credit LiCSAR and NISAR when those layers are actually shown.
   - The case-study text shouldn't promise an interferogram if there isn't one.
4. **Test** the case study plus 2 other Myanmar pins.
5. **By 15:00:** a 30-second demo video (case study → second pin → toggle NISAR) and the project page.

## Needed from the data teammate
1. **Interferogram `data/geo.unw.tif`: the only missing file, and needed by 14:00 to make the demo.**
   - Source: a COMET LiCSAR unwrapped interferogram (`*.geo.unw.tif`) for a frame covering Mandalay / the Sagaing Fault. One date before 28 Mar 2025 and one after (e.g. a pair spanning ~2025-03-2x → 2025-04-0x).
   - The app expects a single band of unwrapped phase in **radians**, in WGS84 (EPSG:4326, which is LiCSAR's default for `geo` files). 0 or NaN is treated as nodata. Noise near the rupture is expected.
   - **`.gitignore` excludes `data/*.tif`**, so don't commit it. Give the app owner the file directly (USB, Drive or chat) to copy into `data/`. Try to keep it under about 50 MB because the venue internet is slow.
   - If it can't be ready by 14:00, say so. We'll demo without it, and the app already skips it automatically.
2. **Check the NISAR image's location** (low priority).
   - The PNG is saved on its native projected grid, and the bounds are the lat/lon envelope of that grid's corners. So the overlay may be slightly offset or skewed compared with a true reprojection. That's acceptable for a demo.
   - The western part (lon 91.47–92.1) falls outside the Myanmar map lock and will be clipped at the edge of the map. That's fine; no action needed.
3. **Project page content** (if you have time after 14:00):
   - **Dataset list:** Sentinel-1 / ESA via GEE; COMET LiCSAR; the NISAR GCOV sample via ASF, with its granule ID and date.
   - **Limits paragraph:** the brightness change is not a measure of how far the ground moved; the stats are estimates; NISAR launched after the quake, so the NISAR layer is a capability sample, not quake data.
   - **AI declaration:** "Code scaffolding and explanations generated with Claude; integration, data sourcing and testing by the team".

## Science and honesty rules (both of us must follow)
- **Labels:** call Sentinel-1 "Sentinel-1 (ESA)", never NISAR.
- **No displacement claims from GEE:** GEE only has amplitude (brightness), not phase, so the drop-a-pin tool cannot measure how far the ground moved. Only the interferogram can.
- **Fringe scale:** one interferogram colour cycle is λ/2 of line-of-sight motion. That's about 2.8 cm for Sentinel-1 and about 12 cm for NISAR L-band.
- **NISAR timing:** NISAR launched in July 2025, after the quake. Its 4 Oct 2026 sample shows L-band capability, **not** earthquake data.
- **Numbers:** no hard-coded or made-up numbers. Every metric must be computed.

## Notes for running it on another machine
- You need `earthengine authenticate` with a Google account that has access to project `engaged-oarlock-432211-q9`, or change `GEE_PROJECT` in `app.py`.
- On Windows user installs, `streamlit` and `earthengine` may not be on PATH. Use `python -m streamlit run app.py` and the full path to `earthengine.exe`.
