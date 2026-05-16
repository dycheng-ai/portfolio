"""
Pull NOAA GOES-16 GLM flash data from S3 and aggregate by US state per day.

Output CSV columns:
  state_abbr, state_name, date, n_files, n_flash_raw, stride, n_flash_est
"""

import s3fs
import xarray as xr
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import datetime
import io
import sys

# ── Config ──────────────────────────────────────────────────────────────────
BUCKET = "noaa-goes16"
PRODUCT = "GLM-L2-LCFA"
STRIDE = 90          # sample every 90th file (~1 per 30 min out of ~4,320/day)
START_DATE = datetime.date(2023, 7, 1)
END_DATE   = datetime.date(2023, 7, 7)   # one week; expand as needed
OUT_CSV = "glm_flash_by_state.csv"

# ── US state boundaries (Natural Earth via geopandas) ───────────────────────
print("Loading US state boundaries...")
states_url = (
    "https://raw.githubusercontent.com/PublicaMundi/MappingAPI/"
    "master/data/geojson/us-states.json"
)
try:
    states = gpd.read_file(states_url)
    states = states.rename(columns={"name": "state_name"})
    # add abbreviations via a lookup
    abbr_map = {
        "Alabama":"AL","Alaska":"AK","Arizona":"AZ","Arkansas":"AR","California":"CA",
        "Colorado":"CO","Connecticut":"CT","Delaware":"DE","Florida":"FL","Georgia":"GA",
        "Hawaii":"HI","Idaho":"ID","Illinois":"IL","Indiana":"IN","Iowa":"IA",
        "Kansas":"KS","Kentucky":"KY","Louisiana":"LA","Maine":"ME","Maryland":"MD",
        "Massachusetts":"MA","Michigan":"MI","Minnesota":"MN","Mississippi":"MS",
        "Missouri":"MO","Montana":"MT","Nebraska":"NE","Nevada":"NV","New Hampshire":"NH",
        "New Jersey":"NJ","New Mexico":"NM","New York":"NY","North Carolina":"NC",
        "North Dakota":"ND","Ohio":"OH","Oklahoma":"OK","Oregon":"OR","Pennsylvania":"PA",
        "Rhode Island":"RI","South Carolina":"SC","South Dakota":"SD","Tennessee":"TN",
        "Texas":"TX","Utah":"UT","Vermont":"VT","Virginia":"VA","Washington":"WA",
        "West Virginia":"WV","Wisconsin":"WI","Wyoming":"WY","District of Columbia":"DC",
    }
    states["state_abbr"] = states["state_name"].map(abbr_map)
    states = states.dropna(subset=["state_abbr"])
    print(f"  Loaded {len(states)} states.")
except Exception as e:
    print(f"Failed to load state boundaries: {e}")
    sys.exit(1)

# ── Connect to S3 (anonymous) ────────────────────────────────────────────────
fs = s3fs.S3FileSystem(anon=True)

records = []

current = START_DATE
while current <= END_DATE:
    year  = current.year
    doy   = current.timetuple().tm_yday   # day-of-year
    prefix = f"{BUCKET}/{PRODUCT}/{year}/{doy:03d}/"

    print(f"\n{current}  listing {prefix}")
    try:
        all_files = fs.glob(f"{prefix}**/*.nc")
    except Exception as e:
        print(f"  Could not list {prefix}: {e}")
        current += datetime.timedelta(days=1)
        continue

    sampled = all_files[::STRIDE]
    print(f"  {len(all_files)} files found → sampling {len(sampled)}")

    lats, lons = [], []
    n_ok = 0
    for fpath in sampled:
        try:
            with fs.open(fpath, "rb") as f:
                ds = xr.open_dataset(f, engine="h5netcdf")
                lats.extend(ds["flash_lat"].values.tolist())
                lons.extend(ds["flash_lon"].values.tolist())
                ds.close()
            n_ok += 1
        except Exception:
            pass

    if not lats:
        print("  No flash data retrieved.")
        current += datetime.timedelta(days=1)
        continue

    # Spatial join: flashes → states
    gdf = gpd.GeoDataFrame(
        {"geometry": [Point(lon, lat) for lon, lat in zip(lons, lats)]},
        crs="EPSG:4326",
    )
    joined = gpd.sjoin(gdf, states[["state_abbr", "state_name", "geometry"]],
                       how="left", predicate="within")
    counts = (
        joined.dropna(subset=["state_abbr"])
        .groupby(["state_abbr", "state_name"])
        .size()
        .reset_index(name="n_flash_raw")
    )
    counts["date"] = str(current)
    counts["n_files"] = n_ok
    counts["stride"] = STRIDE
    counts["n_flash_est"] = counts["n_flash_raw"] * STRIDE

    records.append(counts)
    print(f"  Flashes mapped to {len(counts)} states.")

    current += datetime.timedelta(days=1)

# ── Save ─────────────────────────────────────────────────────────────────────
if records:
    df = pd.concat(records, ignore_index=True)
    df = df[["state_abbr", "state_name", "date", "n_files", "n_flash_raw", "stride", "n_flash_est"]]
    df.to_csv(OUT_CSV, index=False)
    print(f"\nSaved {len(df)} rows to {OUT_CSV}")
    print(df.head(10).to_string(index=False))
else:
    print("\nNo data collected.")
