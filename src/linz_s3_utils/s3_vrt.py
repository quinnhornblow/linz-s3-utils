from pathlib import Path

from cloudpathlib import CloudPath

from linz_s3_utils.gdal import build_vrt


def vrt_from_dir(s3_dir: CloudPath, output_vrt: Path, search_extension=".tiff") -> None:
    """Build a VRT file from all files in the given S3 directory."""
    raster_files = sorted(s3_dir.rglob(f"*{search_extension}"), key=str)
    if not raster_files:
        raise FileNotFoundError(f"No {search_extension} files found in {s3_dir}")

    s3_base_name = str(s3_dir.parents[-1].name)  # "nz-elevation"
    s3_resolution = int(s3_dir.parts[-2].split("_")[1][0])  # e.g., "1"
    s3_srs = int(s3_dir.parts[-1])  # e.g., "2193"

    if s3_resolution not in [1, 8]:
        raise ValueError(f"Unexpected resolution {s3_resolution} in {s3_dir}")
    if s3_srs not in [2193, 4326]:
        raise ValueError(f"Unexpected SRS {s3_srs} in {s3_dir}")

    vrt_paths = [
        str(p).replace(
            f"s3://{s3_base_name}/",
            f"/vsicurl/https://{s3_base_name}.s3-ap-southeast-2.amazonaws.com/",
        )
        for p in raster_files
    ]

    if not output_vrt.parent.exists():
        output_vrt.parent.mkdir(parents=True)

    # Build the VRT
    build_vrt(
        vrt_paths,
        output_vrt,
        resolution=s3_resolution,
        target_aligned_pixels=False,
        srs=s3_srs,
    )
