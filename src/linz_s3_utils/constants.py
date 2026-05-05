from pathlib import Path

S3_ELEVATION_BUCKET = "s3://nz-elevation"

CONTOUR_DEM_S3_DIRECTORY = (
    f"{S3_ELEVATION_BUCKET}/new-zealand/new-zealand-contour/dem_8m/2193"
)
LIDAR_DEM_S3_DIRECTORY = f"{S3_ELEVATION_BUCKET}/new-zealand/new-zealand/dem_1m/2193"

DATA_DIR = Path(__file__).parents[2] / "data"
