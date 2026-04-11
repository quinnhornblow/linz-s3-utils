# linz-s3-utils

Small utilities for working with public LINZ raster data hosted in S3.

The main CLI builds a DEM of all New Zealand by combining:

- 1m LiDAR DEM tiles
- 8m contour DEM tiles

## Requirements

- Python 3.11+
- `uv`
- GDAL available to the Python environment

## Install

```bash
uv sync
```

## Main Usage

Build a 2m New Zealand DEM VRT:

```bash
uv run build-nz-dem --resolution 2
```

This writes:

- `data/new-zealand-contour-8m-dem.vrt`
- `data/new-zealand-lidar-1m-dem.vrt`
- `data/new-zealand-2m-dem.vrt`

To also export a GeoTIFF:

```bash
uv run build-nz-dem --resolution 2 --export_tiff
```

Caution: exporting a tiff at a small resolution will result in a big file!

To rebuild existing outputs:

```bash
uv run build-nz-dem --resolution 2 --overwrite
```

## Command Options

```text
uv run build-nz-dem --resolution <meters> --output_directory <dir> [--export_tiff] [--overwrite]
```

- `--resolution` / `-r`: required output resolution in meters
- `--output_directory` / `-o`: directory for generated files, defaults to `./data`
- `--export_tiff`: export the final DEM as a GeoTIFF as well as a VRT
- `--overwrite`: rebuild files even if they already exist

## Notes

- Source data is read from the public `nz-elevation` S3 bucket.
- The tool uses GDAL VRT building and translation under the hood.
