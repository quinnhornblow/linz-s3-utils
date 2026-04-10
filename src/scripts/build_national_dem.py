from pathlib import Path

from linz_s3_utils.constants import S3_ELEVATION_DIR
from linz_s3_utils.gdal import build_vrt, translate
from linz_s3_utils.vrt import vrt_from_dir

vrt_from_dir(
    S3_ELEVATION_DIR / "new-zealand/new-zealand-contour/dem_8m/2193",
    Path("data/new-zealand-contour-8m-dem.vrt"),
)
vrt_from_dir(
    S3_ELEVATION_DIR / "new-zealand/new-zealand/dem_1m/2193",
    Path("data/new-zealand-lidar-1m-dem.vrt"),
)

build_vrt(
    [
        Path("data/new-zealand-contour-8m-dem.vrt"),
        Path("data/new-zealand-lidar-1m-dem.vrt"),
    ],
    Path("data/new-zealand-100m-dem.vrt"),
    resolution=100,
    resample_alg="bilinear",
    srs=2193,
)

translate(
    Path("data/new-zealand-100m-dem.vrt"),
    Path("data/new-zealand-100m-dem.tiff"),
)
