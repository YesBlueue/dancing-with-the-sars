# Dancing with the SARs — Project Page & Scientific Documentation

## 1. Project Overview
**Dancing with the SARs** is a radar-based surface change detector tailored for Myanmar. Radar microwaves penetrate cloud cover, smoke, and darkness, allowing immediate post-disaster assessments when optical sensors (e.g. Landsat, Sentinel-2) are blinded by monsoon clouds.

The tool combines:
1. **Interactive Global SAR Change Detection (Sentinel-1)**: Near real-time dual-date amplitude backscatter difference over any selected area in Myanmar.
2. **Case Study — 28 March 2025 M7.7 Sagaing Fault Earthquake**: Real computed change metrics around Mandalay and the Sagaing Fault.
3. **Phase Interferometry Layer (COMET LiCSAR)**: Sub-surface line-of-sight ground displacement fringes revealing tectonic rupture mechanics.
4. **Next-Generation Capability Sample (NASA-ISRO NISAR L-Band)**: Sample L-band GCOV backscatter demonstration for future all-weather monitoring.

---

## 2. Dataset Information

| Dataset | Mission / Provider | Coverage & Resolution | Granule / Details |
| :--- | :--- | :--- | :--- |
| **Sentinel-1 GRD** | Copernicus / ESA via Google Earth Engine | Global, 10 m, C-band (5.5 cm wavelength), VV polarization | IW mode collections (2025-03-01 to 2025-04-20) |
| **Interferogram (IFG)** | COMET LiCSAR (NERC / University of Leeds) | Northern Sagaing Fault (24.18°–26.89° N, 95.01°–97.95° E) | Spans **2025-03-24 to 2025-04-05**; unwrapped phase in radians (EPSG:4326) |
| **NISAR L-band GCOV** | NASA-ISRO NISAR via Alaska Satellite Facility (ASF) | Southwestern Myanmar coastal sector (13.32°–16.33° N, 91.47°–94.65° E) | `NISAR_L2_PR_GCOV_032_069_A_009_0005_NASV_A_20261004T231906_20261004T231918_P05023_N_P_J_001.h5` (Acquired **4 Oct 2026**) |

---

## 3. Scientific Limits & Honesty Statement
- **Amplitude vs. Phase**: Radar amplitude change (brightness) reflects changes in surface roughness, structural damage, debris, or flooding. It **does not measure ground displacement distance**.
- **Displacement Quantification**: Only the phase interferogram measures how far the ground shifted. One full color fringe cycle represents $\lambda/2 \approx 2.8\text{ cm}$ of line-of-sight motion for Sentinel-1 C-band (and $\approx 12\text{ cm}$ for NISAR L-band).
- **Radar Estimates**: All computed area metrics (e.g., $1.63\text{ km}^2$ brighter) are pixel-level satellite backscatter estimates, not direct on-the-ground damage surveys.
- **NISAR Capability Sample**: NISAR was launched in July 2025 (subsequent to the March 2025 earthquake event). The included NISAR GCOV layer acquired on 4 October 2026 serves strictly as an illustrative sample demonstrating L-band capability (canopy penetration and reduced decorrelation), not as event data from the earthquake itself.

---

## 4. AI & Attribution Declaration
- **AI Tool Usage**: Code scaffolding and explanations developed with Claude and Gemini; dataset integration, coordinate alignment, NISAR HDF5 transformation, and validation conducted by the project team.
- **Data Attributions**:
  - Copernicus Sentinel-1 data processed by ESA and accessed through Google Earth Engine.
  - LiCSAR unwrapped interferograms provided courtesy of the UK Natural Environment Research Council (NERC) COMET initiative.
  - NISAR sample data provided courtesy of NASA/JPL-Caltech and ISRO via the Alaska Satellite Facility (ASF) DAAC.
