# Script Description

This Python script downloads and clips Sentinel-2 imagery from the public AWS Earth Search using the STAC API.
It fetches visual (RGB) Cloud-Optimized GeoTIFFs (COGs), extracts a user-defined square window around a given latitude and longitude, and saves the results locally with accompanying JSON ingest file for easy importing into GeoDatalytics.

```bash
uv run --script sentinel2Download.py {arguments}
```

## Use Cases

- **Satellite Imagery Clipping**
  Quickly extract a small area (e.g., 10 km × 10 km) of Sentinel-2 data around a point of interest.

- **Change Detection and Time Series Analysis**
  Download multiple cloud-filtered images over a date range for sequential comparison.

- **Data Preprocessing for ML/AI**
  Clip, clean, and organize imagery before feeding it into machine learning pipelines.

## Inputs

The script accepts command-line options via `click`:

- `--lat` _(float, required)_ - Latitude of the point of interest.
- `--lon` _(float, required)_ - Longitude of the point of interest.
- `--start-date` _(str, default `2025-01-01`)_ - Start date in `YYYY-MM-DD` format.
- `--end-date` _(str, default = today)_ - End date in `YYYY-MM-DD` format.
- `--max-results` _(int, default `5`)_ - Maximum number of images to download.
- `--output-dir` _(path, default `sequentialTestRasters`)_ - Directory to save clipped files and JSON file.
- `--cloud-cover` _(float, default `30.0`)_ - Maximum allowed cloud cover percentage of files found.
- `--size-km` _(float, default `10.0`)_ - Size of square window (in kilometers) to clip around the point.

---

## Outputs

- **GeoTIFF files** - Clipped Sentinel-2 visual images (RGB).
- **`sample.json`** - JSON metadata describing datasets, layers, and frames, useful for ingestion into GeoDatalytics.
