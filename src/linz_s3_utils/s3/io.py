from cloudpathlib import CloudPath

from linz_s3_utils.constants import S3_COASTAL_DIR, S3_ELEVATION_DIR, S3_IMAGERY_DIR


def list_elevation_directories() -> list[CloudPath]:
    """List unique directories under S3_ELEVATION_DIR that contain .tiff files."""
    dirs_with_tifs = sorted(
        {tif_path.parent for tif_path in S3_ELEVATION_DIR.rglob("*.tiff")},
        key=str,
    )
    return dirs_with_tifs


def list_coastal_directories() -> list[CloudPath]:
    """List unique directories under S3_COASTAL_DIR that contain .tiff files."""
    dirs_with_tifs = sorted(
        {tif_path.parent for tif_path in S3_COASTAL_DIR.rglob("*.tiff")},
        key=str,
    )
    return dirs_with_tifs


def list_imagery_directories() -> list[CloudPath]:
    """List unique directories under S3_IMAGERY_DIR that contain .tiff files."""
    dirs_with_tifs = sorted(
        {tif_path.parent for tif_path in S3_IMAGERY_DIR.rglob("*.tiff")},
        key=str,
    )
    return dirs_with_tifs


def list_elevation_capture_areas() -> list[CloudPath]:
    """List the elevation capture area files."""
    capture_areas = sorted(
        list(S3_ELEVATION_DIR.rglob("*.geojson")),
        key=str,
    )
    return capture_areas
