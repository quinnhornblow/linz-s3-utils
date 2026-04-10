# https://gdal.org/en/release-3.11/programs/gdal_cli_from_python.html

from osgeo import gdal

gdal.UseExceptions()


def build_vrt(
    input_files,
    output_file,
    resolution=1,
    resample_alg="nearest",
    target_aligned_pixels=True,
    srs=2193,
):
    """Build a VRT file from all files in the given S3 directory."""

    gdal.BuildVRT(
        output_file,
        input_files,
        options=gdal.BuildVRTOptions(
            xRes=resolution,
            yRes=resolution,
            targetAlignedPixels=target_aligned_pixels,
            resampleAlg=resample_alg,
            outputSRS=f"EPSG:{srs}",
            callback=gdal.TermProgress_nocb,
        ),
    )


def translate(input_file, output_file):
    """Translate a VRT file to a GeoTIFF."""

    gdal.Translate(
        output_file,
        input_file,
        options=gdal.TranslateOptions(
            callback=gdal.TermProgress_nocb,
        ),
    )
