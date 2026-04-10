from linz_s3_utils.vrt import vrt_from_dir
from linz_s3_utils.constants import S3_ELEVATION_DIR

from pathlib import Path


def build_nz_dem() -> None:
    vrt_from_dir(
        S3_ELEVATION_DIR / "new-zealand/new-zealand/dem_1m/2193",
        Path("data/new-zealand-lidar-1m-dem.vrt"),
    )
    vrt_from_dir(
        S3_ELEVATION_DIR / "new-zealand/new-zealand-contour/dem_8m/2193",
        Path("data/new-zealand-8m-dem.vrt"),
    )
