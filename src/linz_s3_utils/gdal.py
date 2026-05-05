from osgeo import gdal

# https://gdal.org/en/release-3.11/programs/gdal_cli_from_python.html
gdal.UseExceptions()


COMPRESSION_OPTIONS = {
    "NONE": ["COMPRESS=NONE", "BIGTIFF=IF_NEEDED"],
    "LZW": [
        "COMPRESS=LZW",
        "PREDICTOR=2",
        "NUM_THREADS=ALL_CPUS",
        "BIGTIFF=IF_SAFER",
    ],
    "DEFLATE": [
        "COMPRESS=DEFLATE",
        "PREDICTOR=2",
        "LEVEL=9",
        "NUM_THREADS=ALL_CPUS",
        "BIGTIFF=IF_SAFER",
    ],
    "ZSTD": [
        "COMPRESS=ZSTD",
        "PREDICTOR=2",
        "LEVEL=19",
        "NUM_THREADS=ALL_CPUS",
        "BIGTIFF=IF_SAFER",
    ],
    "LERC": [
        "COMPRESS=LERC",
        "MAX_Z_ERROR=0.001",
        "NUM_THREADS=ALL_CPUS",
        "BIGTIFF=IF_SAFER",
    ],
}


def build_vrt(
    input_files,
    output_file,
    resolution=1,
    resample_alg="bilinear",
    target_aligned_pixels=True,
    srs=None,
):
    """Build a VRT file from a list of input files."""
    print(f"Building VRT: {output_file.name}")

    gdal.BuildVRT(
        output_file,
        input_files,
        options=gdal.BuildVRTOptions(
            xRes=resolution,
            yRes=resolution,
            targetAlignedPixels=target_aligned_pixels,
            resampleAlg=resample_alg,
            outputSRS=f"EPSG:{srs}" if srs else None,
            callback=gdal.TermProgress_nocb,
        ),
    )
    print()


def export_geotiff(input_file, output_file, compression="NONE"):
    """Translate a VRT file to a GeoTIFF."""
    if compression not in COMPRESSION_OPTIONS:
        supported = ", ".join(sorted(COMPRESSION_OPTIONS))
        raise ValueError(f"Unsupported compression '{compression}'. Use one of: {supported}")

    print(f"Translating {input_file.name} to {output_file.name}")

    gdal.Translate(
        output_file,
        input_file,
        options=gdal.TranslateOptions(
            format="GTiff",
            creationOptions=COMPRESSION_OPTIONS[compression],
            callback=gdal.TermProgress_nocb,
        ),
    )
    print()
