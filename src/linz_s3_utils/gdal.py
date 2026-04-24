from enum import Enum

from osgeo import gdal

# https://gdal.org/en/release-3.11/programs/gdal_cli_from_python.html
gdal.UseExceptions()


class OUTPUT_FORMAT(Enum):  # noqa: D101
    NONE = {
        "format": "GTiff",
        "creationOptions": ["COMPRESS=NONE", "BIGTIFF=IF_NEEDED"],
    }
    LZW = {
        "format": "GTiff",
        "creationOptions": [
            "COMPRESS=LZW",
            "PREDICTOR=2",
            "NUM_THREADS=ALL_CPUS",
            "BIGTIFF=IF_SAFER",
        ],
    }
    DEFLATE = {
        "format": "GTiff",
        "creationOptions": [
            "COMPRESS=DEFLATE",
            "PREDICTOR=2",
            "LEVEL=9",
            "NUM_THREADS=ALL_CPUS",
            "BIGTIFF=IF_SAFER",
        ],
    }
    ZSTD = {
        "format": "GTiff",
        "creationOptions": [
            "COMPRESS=ZSTD",
            "PREDICTOR=2",
            "LEVEL=19",
            "NUM_THREADS=ALL_CPUS",
            "BIGTIFF=IF_SAFER",
        ],
    }
    LERC = {
        "format": "GTiff",
        "creationOptions": [
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


def translate(input_file, output_file, output_config=OUTPUT_FORMAT["NONE"]):
    """Translate a VRT file to a GeoTIFF."""
    print(f"Translating {input_file.name} to {output_file.name}")

    gdal.Translate(
        output_file,
        input_file,
        options=gdal.TranslateOptions(
            format=output_config.value["format"],
            creationOptions=output_config.value["creationOptions"],
            callback=gdal.TermProgress_nocb,
        ),
    )
    print()
