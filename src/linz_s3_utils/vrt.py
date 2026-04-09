from linz_s3_utils.constants import S3_ELEVATION_DIR
from linz_s3_utils.gdal import mosaic


def build_vrt(s3_dir, output_vrt, extension=".tiff"):
    """Build a VRT file from all files in the given S3 directory."""
    tif_files = sorted(s3_dir.rglob(f"*{extension}"), key=str)
    if not tif_files:
        print(f"No {extension} files found in {s3_dir}")
        return

    s3_base_name = s3_dir.parents[-1].name

    vrt_paths = [
        str(p).replace(
            f"s3://{s3_base_name}/",
            f"/vsicurl/https://{s3_base_name}.s3-ap-southeast-2.amazonaws.com/",
        )
        for p in tif_files
    ]

    # Build the VRT command
    mosaic(vrt_paths, output_vrt)


if __name__ == "__main__":
    build_vrt(S3_ELEVATION_DIR / "new-zealand/new-zealand/dem_1m/2193", "output2.vrt")
