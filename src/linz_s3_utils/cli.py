import argparse
from pathlib import Path

from linz_s3_utils.constants import S3_ELEVATION_DIR
from linz_s3_utils.gdal import build_vrt, translate
from linz_s3_utils.s3_vrt import vrt_from_dir


def build_nz_dem() -> None:
    """Build a DEM for all of New Zealand from the 1m LIDAR and 8m contour data."""
    parser = argparse.ArgumentParser(
        prog="build_nz_dem",
        description="Build a DEM for New Zealand from the 1m LIDAR and 8m contour data.",
    )

    parser.add_argument(
        "-r",
        "--resolution",
        required=True,
        type=int,
        help="Resolution of the output image in meters.",
    )

    parser.add_argument(
        "-o",
        "--output_directory",
        type=Path,
        default=Path("data"),
        help="Path to the output directory.",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Whether to overwrite existing files.",
    )

    parser.add_argument(
        "--export_tiff",
        action="store_true",
        help="Whether to export the final DEM as a GeoTIFF.",
    )

    args = parser.parse_args()

    output_dir = Path(args.output_directory)

    if not output_dir.exists():
        raise FileNotFoundError(f"Output directory {output_dir} does not exist.")

    nz_8m_vrt = output_dir / "new-zealand-contour-8m-dem.vrt"
    nz_1m_vrt = output_dir / "new-zealand-lidar-1m-dem.vrt"
    output_vrt = output_dir / f"new-zealand-{args.resolution}m-dem.vrt"
    output_tiff = output_dir / f"new-zealand-{args.resolution}m-dem.tiff"

    if not nz_8m_vrt.exists() or args.overwrite:
        vrt_from_dir(
            S3_ELEVATION_DIR / "new-zealand/new-zealand-contour/dem_8m/2193",
            nz_8m_vrt,
        )

    if not nz_1m_vrt.exists() or args.overwrite:
        vrt_from_dir(
            S3_ELEVATION_DIR / "new-zealand/new-zealand/dem_1m/2193",
            nz_1m_vrt,
        )

    if not output_vrt.exists() or args.overwrite:
        build_vrt(
            [
                nz_8m_vrt,
                nz_1m_vrt,
            ],
            output_vrt,
            resolution=args.resolution,
        )

    if args.export_tiff:
        if not output_tiff.exists() or args.overwrite:
            translate(
                output_vrt,
                output_tiff,
            )
