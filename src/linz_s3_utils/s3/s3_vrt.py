from pathlib import Path

from cloudpathlib import CloudPath

from linz_s3_utils.gdal import build_vrt


def s3_path_to_gdal_url(path: CloudPath) -> str:
    """Convert an s3:// path into a GDAL /vsicurl/ path."""
    bucket = path.bucket
    key = path.key
    return f"/vsicurl/https://{bucket}.s3-ap-southeast-2.amazonaws.com/{key}"


def build_vrt_from_s3_directory(
    s3_directory: str | CloudPath,
    output_vrt: Path,
    search_extension: str = ".tiff",
) -> None:
    """Build a VRT file from all files in the given S3 directory."""
    cloud_directory = CloudPath(s3_directory) if isinstance(s3_directory, str) else s3_directory

    raster_files = sorted(cloud_directory.rglob(f"*{search_extension}"), key=str)
    if not raster_files:
        raise FileNotFoundError(
            f"No {search_extension} files found in {cloud_directory}"
        )

    s3_resolution_text = cloud_directory.parts[-2].split("_")[1]
    s3_resolution = int(s3_resolution_text.replace("m", ""))
    s3_srs = int(cloud_directory.parts[-1])

    if s3_resolution not in [1, 8]:
        raise ValueError(
            f"Unexpected resolution {s3_resolution} in {cloud_directory}"
        )
    if s3_srs not in [2193, 4326]:
        raise ValueError(f"Unexpected SRS {s3_srs} in {cloud_directory}")

    gdal_raster_paths = [s3_path_to_gdal_url(path) for path in raster_files]

    build_vrt(
        gdal_raster_paths,
        output_vrt,
        resolution=s3_resolution,
        resample_alg="nearest",
        target_aligned_pixels=False,
        srs=s3_srs,
    )
