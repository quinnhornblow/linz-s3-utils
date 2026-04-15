import pytest

from linz_s3_utils.constants import S3_ELEVATION_DIR
from linz_s3_utils.gdal import OUTPUT_FORMAT, translate
from linz_s3_utils.s3_vrt import vrt_from_dir


@pytest.fixture(scope="module")
def vrt(tmp_path_factory):
    """Create a VRT file from the input data."""
    tmp_path = tmp_path_factory.mktemp("compression")
    vrt_from_dir(
        S3_ELEVATION_DIR / "southland/stewart-island-rakiura-oban_2021/dem_1m/2193",
        tmp_path / "input.vrt",
    )
    return tmp_path / "input.vrt"


@pytest.mark.parametrize("co", ["NONE", "LERC", "LZW", "DEFLATE", "ZSTD"])
def test_compression_options(co, vrt, tmp_path):
    """Test that the compression options are valid."""
    translate(
        vrt,
        tmp_path / "output.tiff",
        output_config=OUTPUT_FORMAT[co],
    )
