import argparse
from pathlib import Path

from linz_s3_utils.constants import DATA_DIR
from linz_s3_utils.dem import build_new_zealand_dem


def build_nz_dem(argv: list[str] | None = None) -> None:
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
        "--output-directory",
        type=Path,
        default=DATA_DIR,
        help="Path to the output directory.",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Whether to overwrite existing files.",
    )

    parser.add_argument(
        "--export-tiff",
        action="store_true",
        help="Whether to export the final DEM as a GeoTIFF.",
    )

    parser.add_argument(
        "--compression",
        choices=["NONE", "LERC", "LZW", "DEFLATE", "ZSTD"],
        default="NONE",
        help="Compression method to use for the output GeoTIFF.",
    )

    args = parser.parse_args(argv)

    build_new_zealand_dem(
        output_directory=Path(args.output_directory),
        resolution=args.resolution,
        overwrite=args.overwrite,
        export_tiff=args.export_tiff,
        compression=args.compression,
    )
