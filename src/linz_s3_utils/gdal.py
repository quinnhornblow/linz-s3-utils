from osgeo import gdal

# https://gdal.org/en/release-3.11/programs/gdal_cli_from_python.html
gdal.UseExceptions()


def build_vrt(
    input_files,
    output_file,
    resolution=1,
    resample_alg="nearest",
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


def translate(input_file, output_file):
    """Translate a VRT file to a GeoTIFF."""
    print(f"Translating {input_file.name} to {output_file.name}")

    gdal.Translate(
        output_file,
        input_file,
        options=gdal.TranslateOptions(
            callback=gdal.TermProgress_nocb,
        ),
    )
    print()
