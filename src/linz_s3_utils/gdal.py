import subprocess
# import osgeo.gdal
# https://gdal.org/en/stable/programs/gdal_cli_from_python.html#gdal-cli-from-python


def mosaic():
    """Build a VRT file from all files in the given S3 directory."""

    # Build the command
    gdal_command = "C:/OSGeo4W/bin/gdal.exe raster mosaic --help"

    # Execute the command
    try:
        subprocess.run(gdal_command.split(" "), check=True)
    except subprocess.CalledProcessError as e:
        # print(e.stderr)
        raise e


if __name__ == "__main__":
    mosaic()
