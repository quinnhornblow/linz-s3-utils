# https://gdal.org/en/release-3.11/programs/gdal_cli_from_python.html

from osgeo import gdal

gdal.UseExceptions()


def build_vrt(input_files, output_file, resolution=1, srs=2193):
    """Build a VRT file from all files in the given S3 directory."""

    gdal.BuildVRT(
        output_file,
        input_files,
        options=gdal.BuildVRTOptions(
            resampleAlg="nearest",
            xRes=resolution,
            yRes=resolution,
            outputSRS=f"EPSG:{srs}",
            callback=gdal.TermProgress_nocb,
        ),
    )
