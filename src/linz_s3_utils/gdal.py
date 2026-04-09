# import subprocess
from osgeo import gdal

# https://gdal.org/en/stable/programs/gdal_cli_from_python.html#gdal-cli-from-python


def mosaic(input_files, output_file):
    """Build a VRT file from all files in the given S3 directory."""

    gdal.alg.raster.mosaic(
        input_files,
        output_file,
        resolution="1,1",
        # progress=True,
    )
