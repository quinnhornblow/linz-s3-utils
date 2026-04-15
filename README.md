# linz-s3-utils

Small utilities for working with public LINZ raster data hosted in S3.

## Motivation

The public LINZ data is an incredible resource. It is easily accessible through the [LINZ Data Service](https://data.linz.govt.nz/) and more recently via S3. There are two main national DEM datasets. The 8m DEM derived from contours and the 1m LiDAR DEM which is incomplete.

I have found it useful (for example watershed analysis) to have a complete, accurate, and manageable DEM that covers all of New Zealand.

The main CLI builds a DEM of all New Zealand by combining:

- 1m LiDAR DEM tiles (preference)
- 8m contour DEM tiles (filling areas without LiDAR)

Specifying an output resolutions makes it easy to create .tiff files of a manageable size depending on storage and hardware limitations.

### Future

While this package has mainly been developed with the nz-elevation data in mind it should also work (or could easily be extended) to support the nz-imagery and nz-coastal S3 datasets.

## Requirements

- Python 3.11+
- `uv`
- GDAL available to the Python environment


To install:

```bash
uv sync
```

## Main Usage

Build a 100m New Zealand DEM VRT:

```bash
uv run build-nz-dem --resolution 100
```

This writes:

- data/new-zealand-contour-8m-dem.vrt
- data/new-zealand-lidar-1m-dem.vrt
- data/new-zealand-100m-dem.vrt


To also export a GeoTIFF:

```bash
uv run build-nz-dem --resolution 100 --export_tiff
```

> [!NOTE]
>
> Exporting a tiff at a small resolution will result in a big file!
>

To rebuild or overwrite existing outputs (useful when new LiDAR gets added):

```bash
uv run build-nz-dem --resolution 100 --overwrite
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
- The tool uses GDAL buildvrt and translate under the hood.
- Default resampling options are TargetAlignedPixels=True and method='bilinear'.
- tiff compression using the same LERC configuration discussed [here](https://github.com/linz/elevation/blob/master/docs/tiff-compression/README.md) but any supported GDAL creation options can be specified.

## Docker

This package depends on GDAL which can be difficult to install on some systems. For convenience you can run docker with the following configuration:

```
docker build -t linz-s3-utils .
docker run --rm -v "[path_to_output_location]:/app/data" linz-s3-utils -r 100
```

