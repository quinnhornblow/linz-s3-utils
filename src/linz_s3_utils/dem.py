from pathlib import Path

from linz_s3_utils.constants import CONTOUR_DEM_S3_DIRECTORY, LIDAR_DEM_S3_DIRECTORY


def build_new_zealand_dem(
    output_directory: Path,
    resolution: int,
    overwrite: bool,
    export_tiff: bool,
    compression: str,
) -> None:
    """Build a complete New Zealand DEM from contour and lidar data."""
    from linz_s3_utils.gdal import build_vrt, export_geotiff
    from linz_s3_utils.s3.s3_vrt import build_vrt_from_s3_directory

    if not output_directory.exists():
        raise FileNotFoundError(f"Output directory does not exist: {output_directory}")

    contour_vrt = output_directory / "new-zealand-contour-8m-dem.vrt"
    lidar_vrt = output_directory / "new-zealand-lidar-1m-dem.vrt"
    combined_vrt = output_directory / f"new-zealand-{resolution}m-dem.vrt"
    combined_tiff = output_directory / f"new-zealand-{resolution}m-dem.tiff"

    if overwrite or not contour_vrt.exists():
        build_vrt_from_s3_directory(CONTOUR_DEM_S3_DIRECTORY, contour_vrt)

    if overwrite or not lidar_vrt.exists():
        build_vrt_from_s3_directory(LIDAR_DEM_S3_DIRECTORY, lidar_vrt)

    if overwrite or not combined_vrt.exists():
        build_vrt([contour_vrt, lidar_vrt], combined_vrt, resolution=resolution)

    if export_tiff and (overwrite or not combined_tiff.exists()):
        export_geotiff(combined_vrt, combined_tiff, compression=compression)
