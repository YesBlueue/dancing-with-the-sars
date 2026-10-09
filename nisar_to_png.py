import sys, json, os
import h5py
import numpy as np
import matplotlib.pyplot as plt
from pyproj import Transformer

path = sys.argv[1]

with h5py.File(path, "r") as f:
    grids_path = "/science/LSAR/GCOV/grids"
    if grids_path in f:
        available_grids = list(f[grids_path].keys())
        grid_name = "frequencyA" if "frequencyA" in available_grids else available_grids[0]
        GRID = f"{grids_path}/{grid_name}"
    else:
        GRID = "/science/LSAR/GCOV/grids/frequencyA"

    if GRID not in f:
        print("Grid path not found. Datasets in file:")
        f.visit(lambda n: print(" ", n) if "GCOV" in n else None)
        sys.exit(1)
        
    g = f[GRID]
    pols = [k for k in ("HHHH", "VVVV", "HVHV") if k in g]
    if not pols:
        print("No matching polarization dataset found. Available keys:", list(g.keys()))
        sys.exit(1)
    pol = pols[0]
    ds = g[pol]
    MAX_PX = 2000
    step = max(1, int(max(ds.shape) / MAX_PX))
    arr = ds[::step, ::step].astype("float32")
    x = g["xCoordinates"][::step]
    y = g["yCoordinates"][::step]
    epsg = int(g["projection"].attrs.get("epsg_code", g["projection"][()]))

arr[arr <= 0] = np.nan
db = 10 * np.log10(arr)
lo, hi = np.nanpercentile(db, [2, 98])
norm = np.clip((db - lo) / (hi - lo), 0, 1)
rgba = plt.cm.gray(np.nan_to_num(norm))
rgba[np.isnan(db), 3] = 0

os.makedirs("data", exist_ok=True)
plt.imsave("data/nisar.png", rgba)

t = Transformer.from_crs(epsg, 4326, always_xy=True)
xs = [x.min(), x.max(), x.min(), x.max()]
ys = [y.min(), y.min(), y.max(), y.max()]
lons, lats = t.transform(xs, ys)
bounds = [[min(lats), min(lons)], [max(lats), max(lons)]]
with open("data/nisar_bounds.json", "w") as fp:
    json.dump({"bounds": bounds, "polarization": pol, "source": os.path.basename(path)}, fp)
print("Successfully generated data/nisar.png and data/nisar_bounds.json")
